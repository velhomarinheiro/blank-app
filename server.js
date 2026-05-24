'use strict';
const express  = require('express');
const http     = require('http');
const { Server } = require('socket.io');
const path     = require('path');
const { ORDER_OF_BATTLE }  = require('./shared/order_of_battle');
const { COMBAT_CONFIG }    = require('./shared/combat_config');
const { resolveEngagement, getWeaponQuantity, getWeaponRange } = require('./shared/combat_engine');

const PORT   = process.env.PORT || 3000;
const GRID_W = 16;
const GRID_H = 10;

// ─── Terrain (mirror of public/js/terrain.js) ────────────────────────────────
const T_LAND = 0, T_SHALLOW = 1, T_SHELF = 2, T_DEEP = 3, T_OIL = 4;
const TERRAIN_MAP = [
  [0,0,0,0,0,0,1,2,3,3,3,3,3,3,3,3],
  [0,0,0,0,0,1,1,2,3,3,3,3,3,3,3,3],
  [0,0,0,0,1,1,2,4,3,3,3,3,3,3,3,3],
  [0,0,0,1,1,2,4,4,3,3,3,3,3,3,3,3],
  [0,0,1,1,2,4,4,2,3,3,3,3,3,3,3,3],
  [0,1,1,2,4,4,2,3,3,3,3,3,3,3,3,3],
  [1,1,2,4,4,2,3,3,3,3,3,3,3,3,3,3],
  [1,2,2,4,2,2,3,3,3,3,3,3,3,3,3,3],
  [1,2,2,2,2,3,3,3,3,3,3,3,3,3,3,3],
  [1,2,2,2,3,3,3,3,3,3,3,3,3,3,3,3],
];
function getTerrain(col, row) {
  if (row < 0 || row >= GRID_H || col < 0 || col >= GRID_W) return T_LAND;
  return TERRAIN_MAP[row][col];
}
function canEnterTerrain(category, terrain) {
  if (category === 'air')       return true;
  if (category === 'land')      return terrain === T_LAND || terrain === T_SHALLOW;
  if (category === 'submarine') return terrain !== T_LAND && terrain !== T_SHALLOW;
  return terrain !== T_LAND; // surface
}

// ─── Display type: primary composition type → counter icon type ───────────────
const COMP_DISPLAY_TYPE = {
  'navio_aeródromo':       'carrier',
  'navio_doca':            'amphib',
  'navio_desembarque':     'amphib',
  'fragata':               'fragata',
  'corveta':               'corveta',
  'destroier':             'destroier',
  'destroyer':             'destroier',
  'cruzador':              'cruzador',
  'navio_patoc':           'patrulha_oc',
  'navio_patrulha':        'patrulha_c',
  'navio_logistico':       'logistico',
  'navio_tanque':          'tanque',
  'submarino_nuclear':     'sub_nuclear',
  'submarino_convencional':'submarino',
  'patrulha_maritima':     'patrulha',
  'caca':                  'caca',
  'ataque':                'ataque',
  'aew':                   'aew',
  'helicoptero_ASW':       'helicoptero',
  'helicoptero_ASup':      'helicoptero',
  'bateria_costeira':      'bateria_costeira',
  'bateria_ada':           'bateria_ada',
  'base_naval':            'bateria_ada',
  'plataforma':            'fpso',
  'porto':                 'porto',
};
const DISPLAY_TYPE_FALLBACK = { surface: 'fragata', submarine: 'submarino', air: 'patrulha', land: 'corveta' };

// ─── Range helper ─────────────────────────────────────────────────────────────
function rangeAgainst(rangeTable, targetCategory) {
  if (!rangeTable) return 0;
  return Number(rangeTable[targetCategory] || 0);
}

// ─── Hex math (odd-q offset, flat-top) — matches client hex.js ──────────────
function oddqToCube(col, row) {
  const x = col;
  const z = row - (col - (col & 1)) / 2;
  return { x, y: -x - z, z };
}
function cubeToOddq(x, z) { return { col: x, row: z + (x - (x & 1)) / 2 }; }
const CUBE_DIRS = [
  {dx:+1,dy:-1,dz:0},{dx:+1,dy:0,dz:-1},{dx:0,dy:+1,dz:-1},
  {dx:-1,dy:+1,dz:0},{dx:-1,dy:0,dz:+1},{dx:0,dy:-1,dz:+1},
];
function hexNeighbors(col, row) {
  const c = oddqToCube(col, row);
  return CUBE_DIRS.map(d => cubeToOddq(c.x+d.dx, c.z+d.dz))
    .filter(({col:nc,row:nr}) => nc>=0 && nc<GRID_W && nr>=0 && nr<GRID_H);
}
function hexDist(c1,r1,c2,r2) {
  const a=oddqToCube(c1,r1), b=oddqToCube(c2,r2);
  return Math.max(Math.abs(a.x-b.x), Math.abs(a.y-b.y), Math.abs(a.z-b.z));
}

// ─── Fog of war ──────────────────────────────────────────────────────────────
function saveMovementSnapshot(state) {
  state.movementSnapshot = {};
  for (const u of state.units) {
    state.movementSnapshot[u.id] = { col: u.col, row: u.row };
  }
}

function stateFor(state, team) {
  const night = state.period === 'night';

  // During movement phase, show enemy units at their pre-movement positions
  // so moves are hidden until both sides commit (simultaneous movement reveal).
  const enemyActual = state.units.filter(u => u.team !== team && u.hp > 0);
  const enemies = (state.phase === 'movement' && state.movementSnapshot)
    ? enemyActual.map(u => {
        const snap = state.movementSnapshot[u.id];
        return snap ? { ...u, col: snap.col, row: snap.row } : u;
      })
    : enemyActual;

  const mine = state.units.filter(u => u.team === team && u.hp > 0);

  const detected = enemies.filter(enemy => {
    const stealthy  = !!enemy.stealthy;
    const deepBonus = getTerrain(enemy.col, enemy.row) === T_DEEP ? 1 : 0;
    return mine.some(f => {
      let range = stealthy
        ? rangeAgainst(f.detectionRange, 'submarine') - deepBonus
        : rangeAgainst(f.detectionRange, enemy.category);
      // Submarines use sonar — unaffected by daylight
      if (night && f.category !== 'submarine') range -= stealthy ? 1 : 2;
      return range >= 1 && hexDist(f.col, f.row, enemy.col, enemy.row) <= range;
    });
  }).map(e => ({ ...e, detected: true }));

  return {
    ...state,
    units:       [...state.units.filter(u => u.team === team), ...detected],
    blueAttacks: team === 'blue' ? state.blueAttacks : (state.blueAttacks !== null ? '✓' : null),
    redAttacks:  team === 'red'  ? state.redAttacks  : (state.redAttacks  !== null ? '✓' : null),
  };
}

// ─── Weapon priority per target category ─────────────────────────────────────
const WEAPON_PRIORITY = {
  surface:   ['ascm', 'asbm', 'mss', 'torpedo', 'airAttack', 'navalGun'],
  submarine: ['asw', 'torpedo'],
  air:       ['airDefense', 'airAttack'],
  land:      ['lacm', 'airAttack', 'navalGun'],
};

function selectBestWeapon(attacker, target, dist) {
  const priority = WEAPON_PRIORITY[target.category] || [];
  for (const wpnType of priority) {
    const qty = getWeaponQuantity(attacker, wpnType);
    if (qty <= 0) continue;
    const profile = COMBAT_CONFIG.weaponProfiles?.[wpnType];
    if (!profile) continue;
    if (!profile.targets.includes(target.category)) continue;
    const range = getWeaponRange(attacker, wpnType);
    if (dist <= range) return wpnType;
  }
  return null;
}

// ─── Unit factory ─────────────────────────────────────────────────────────────
function makeUnit(team, spec) {
  const pos     = spec.position || spec.start || { col: 0, row: 0 };
  const weapons = spec.weapons ? JSON.parse(JSON.stringify(spec.weapons)) : {};
  return {
    id:            spec.id,
    team,
    name:          spec.name,
    category:      spec.category,
    type:          (spec.composition && spec.composition[0] && COMP_DISPLAY_TYPE[spec.composition[0].type]) || DISPLAY_TYPE_FALLBACK[spec.category] || 'fragata',
    composition:   spec.composition || [],
    movement:      spec.movement,
    detectionRange: spec.detectionRange,
    attackRange:   spec.attackRange,
    col:           pos.col,
    row:           pos.row,
    hp:            spec.stayingPower,
    maxHp:         spec.stayingPower,
    stealthy:      spec.category === 'submarine',
    moved:         false,
    weapons,
    initWeapons:   JSON.parse(JSON.stringify(weapons)),
    capabilities:  spec.capabilities ? { ...spec.capabilities } : {},
  };
}

function initialUnits() {
  const units = [];
  for (const spec of ORDER_OF_BATTLE.forces.blue) {
    units.push(makeUnit('blue', spec));
  }
  for (const spec of ORDER_OF_BATTLE.forces.red) {
    units.push(makeUnit('red', spec));
  }
  return units;
}

function newGame() {
  const state = {
    turn: 1, period: 'day', phase: 'movement',
    blueDone: false, redDone: false,
    blueAttacks: null, redAttacks: null,
    units: initialUnits(),
    log: ['──── Turno 1 · Período Diurno ────', 'Fase de Movimentação iniciada.'],
    winner: null,
    movementSnapshot: {},
  };
  saveMovementSnapshot(state);
  return state;
}

// ─── Combat resolution ────────────────────────────────────────────────────────
function resolveCombat(state) {
  const results = [];
  const all = [...(state.blueAttacks||[]), ...(state.redAttacks||[])];

  for (const atk of all) {
    const att = state.units.find(u => u.id === atk.attackerId && u.hp > 0);
    const tgt = state.units.find(u => u.id === atk.targetId   && u.hp > 0);
    if (!att || !tgt) continue;

    const dist = hexDist(att.col, att.row, tgt.col, tgt.row);
    const r = {
      attacker: att.name, attackerTeam: att.team,
      target: tgt.name,   targetTeam: tgt.team,
      targetId: tgt.id, hit: false, damage: 0, destroyed: false,
    };

    const weaponType = selectBestWeapon(att, tgt, dist);
    if (!weaponType) {
      state.log.unshift(`⚠ ${att.name} sem armamento válido para ${tgt.name}.`);
      r.outOfRange = true; results.push(r); continue;
    }

    const eng = resolveEngagement({ attacker: att, defender: tgt, weaponType, amount: 1, distance: dist });
    if (!eng.ok) {
      state.log.unshift(`⚠ ${att.name} → ${tgt.name}: ${eng.reason}`);
      r.outOfRange = true; results.push(r); continue;
    }

    r.weaponType   = eng.weaponType;
    r.weaponLabel  = eng.weaponLabel;
    r.launched     = eng.launched;
    r.interception = eng.interception;
    r.attackRolls  = eng.attackRolls;
    r.damage       = eng.totalDamage;
    r.destroyed    = eng.destroyed;
    r.hit          = eng.totalDamage > 0;
    r.remainingHp  = eng.remainingHp;

    if (eng.destroyed) {
      state.log.unshift(`💥 ${tgt.name}(${tgt.team}) DESTRUÍDO por ${att.name} [${eng.weaponLabel}]`);
    } else if (eng.totalDamage > 0) {
      const intStr = eng.interception.intercepted > 0 ? ` (${eng.interception.intercepted} intercept.)` : '';
      state.log.unshift(`✓ ${att.name} → ${tgt.name} −${eng.totalDamage}SP [${eng.weaponLabel}${intStr}]`);
    } else {
      const intStr = eng.interception.intercepted > 0 ? ` (${eng.interception.intercepted} intercept.)` : '';
      state.log.unshift(`✗ ${att.name} → ${tgt.name} falhou [${eng.weaponLabel}${intStr}]`);
    }
    results.push(r);
  }

  if (state.log.length > 50) state.log = state.log.slice(0, 50);
  return results;
}

function checkWinner(state) {
  const hasOffense = u =>
    Object.values(u.attackRange || {}).some(v => v > 0) ||
    Object.values(u.weapons      || {}).some(w => w.quantity > 0) ||
    Object.values(u.capabilities || {}).some(v => v > 0);
  const isCombatant = u => hasOffense(u);
  const b = state.units.some(u => u.team === 'blue' && u.hp > 0 && isCombatant(u));
  const r = state.units.some(u => u.team === 'red'  && u.hp > 0 && isCombatant(u));
  if (!b) return 'red'; if (!r) return 'blue'; return null;
}

function nextTurn(state) {
  // ── Reload check (before moved flags are cleared) ────────────────────────────
  const portHexes = new Set(
    state.units.filter(u => u.team === 'blue' && u.hp > 0 && u.type === 'porto')
               .map(u => `${u.col},${u.row}`)
  );
  const blueCarrierHexes = new Set(
    state.units.filter(u => u.team === 'blue' && u.hp > 0 && u.type === 'carrier')
               .map(u => `${u.col},${u.row}`)
  );
  const redCarrierHexes = new Set(
    state.units.filter(u => u.team === 'red' && u.hp > 0 && u.type === 'carrier')
               .map(u => `${u.col},${u.row}`)
  );

  for (const u of state.units) {
    if (u.hp <= 0) continue;
    if (!u.initWeapons || Object.keys(u.initWeapons).length === 0) continue;

    const hexKey = `${u.col},${u.row}`;
    let reload = false;

    if (u.team === 'blue') {
      if (u.category === 'land') {
        reload = true;
      } else if (!u.moved) {
        if (u.category === 'surface' || u.category === 'submarine') {
          reload = portHexes.has(hexKey);
        } else if (u.category === 'air') {
          reload = getTerrain(u.col, u.row) === T_LAND || blueCarrierHexes.has(hexKey);
        }
      }
    } else if (u.team === 'red') {
      if (u.category === 'air' && !u.moved) {
        reload = redCarrierHexes.has(hexKey);
      }
    }

    if (reload) {
      const restored = [];
      for (const [wpn, init] of Object.entries(u.initWeapons)) {
        const cur = u.weapons[wpn]?.quantity ?? 0;
        if (cur < init.quantity) {
          u.weapons[wpn] = { ...init };
          restored.push(wpn.toUpperCase());
        }
      }
      if (restored.length > 0) {
        state.log.unshift(`🔄 ${u.name} recompletou: ${restored.join(', ')}`);
      }
    }
  }

  // ── Advance turn ────────────────────────────────────────────────────────────
  state.units.forEach(u => { u.moved = false; });
  state.period    = state.period === 'day' ? 'night' : 'day';
  if (state.period === 'day') state.turn++;
  state.phase     = 'movement';
  state.blueDone  = state.redDone = false;
  state.blueAttacks = state.redAttacks = null;
  const per = state.period === 'day' ? 'Diurno' : 'Noturno';
  state.log.unshift(`──── Turno ${state.turn} · Período ${per} ────`);
  state.log.unshift('Fase de Movimentação iniciada.');
  if (state.log.length > 50) state.log = state.log.slice(0, 50);
  saveMovementSnapshot(state);
}

// ─── Server ───────────────────────────────────────────────────────────────────
const app    = express();
const server = http.createServer(app);
const io     = new Server(server, { cors: { origin: '*' } });

app.use(express.static(path.join(__dirname, 'public')));
app.get('/',     (_, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')));
app.get('/game', (_, res) => res.sendFile(path.join(__dirname, 'public', 'game.html')));

const rooms = new Map();
function genId() { return Math.random().toString(36).slice(2,8).toUpperCase(); }
function broadcast(room) {
  if (!room.state) return;
  if (room.players.blue) io.to(room.players.blue).emit('game_update', stateFor(room.state,'blue'));
  if (room.players.red)  io.to(room.players.red ).emit('game_update', stateFor(room.state,'red'));
}

io.on('connection', socket => {
  console.log('+ connect', socket.id);

  socket.on('create_room', () => {
    const id = genId();
    rooms.set(id, { id, players:{blue:socket.id,red:null}, state:null });
    socket.data.roomId=id; socket.data.team='blue';
    socket.join(id);
    socket.emit('room_created',{roomId:id,team:'blue'});
  });

  socket.on('join_room', ({roomId}) => {
    const room=rooms.get(roomId?.toUpperCase?.());
    if (!room)           { socket.emit('join_error','Sala não encontrada.'); return; }
    if (room.players.red){ socket.emit('join_error','Sala cheia.');          return; }
    room.players.red=socket.id; socket.data.roomId=room.id; socket.data.team='red';
    socket.join(room.id);
    room.state=newGame();
    io.to(room.players.blue).emit('game_start',{team:'blue',state:stateFor(room.state,'blue')});
    socket.emit('game_start',{team:'red',state:stateFor(room.state,'red')});
  });

  // ── Movement ──────────────────────────────────────────────────────────────
  socket.on('commit_moves', ({moves}) => {
    const room=rooms.get(socket.data.roomId);
    if (!room?.state) return;
    const {state}=room, {team}=socket.data;

    if (state.phase!=='movement')                  { socket.emit('action_error','Não é a fase de movimentação.'); return; }
    if (state[team==='blue'?'blueDone':'redDone']) { socket.emit('action_error','Você já encerrou a movimentação.'); return; }

    // Validate all paths before applying any
    for (const {unitId, path} of (moves||[])) {
      if (!Array.isArray(path)||path.length<2) continue;
      const unit=state.units.find(u=>u.id===unitId&&u.team===team&&u.hp>0);
      if (!unit) { socket.emit('action_error',`Unidade ${unitId} inválida.`); return; }
      if (unit.movement === 0) { socket.emit('action_error',`${unit.name}: unidade fixa.`); return; }
      if (path[0].col!==unit.col||path[0].row!==unit.row) { socket.emit('action_error',`Caminho inválido para ${unit.name}.`); return; }
      if (path.length-1>unit.movement) { socket.emit('action_error',`${unit.name}: caminho excede alcance máximo.`); return; }
      for (let i=1;i<path.length;i++) {
        const {col,row}=path[i];
        if (col<0||col>=GRID_W||row<0||row>=GRID_H) { socket.emit('action_error',`${unit.name}: posição fora do tabuleiro.`); return; }
        if (hexDist(path[i-1].col,path[i-1].row,col,row)!==1) { socket.emit('action_error',`${unit.name}: passo não adjacente.`); return; }
        if (!canEnterTerrain(unit.category,getTerrain(col,row))) { socket.emit('action_error',`${unit.name}: terreno intransponível em ${String.fromCharCode(65+col)}${row+1}.`); return; }
      }
    }

    // Apply all moves
    for (const {unitId, path} of (moves||[])) {
      if (!Array.isArray(path)||path.length<2) continue;
      const unit=state.units.find(u=>u.id===unitId&&u.team===team&&u.hp>0);
      if (!unit) continue;
      const dest=path[path.length-1];
      unit.col=dest.col; unit.row=dest.row; unit.moved=true;
      state.log.unshift(`${unit.name}(${team}) → ${String.fromCharCode(65+dest.col)}${dest.row+1}`);
    }

    if (team==='blue') state.blueDone=true; else state.redDone=true;
    if (state.blueDone&&state.redDone) {
      state.phase='combat';
      state.log.unshift('Fase de Combate iniciada. Declare seus ataques.');
    } else {
      const waiting=team==='blue'?'Força Vermelha':'Força Azul';
      state.log.unshift(`${team==='blue'?'Força Azul':'Força Vermelha'} encerrou a movimentação. Aguardando ${waiting}...`);
    }
    if (state.log.length>30) state.log=state.log.slice(0,30);
    broadcast(room);
  });

  // ── Combat ────────────────────────────────────────────────────────────────
  socket.on('declare_attacks', attacks => {
    const room=rooms.get(socket.data.roomId);
    if (!room?.state) return;
    const {state}=room, {team}=socket.data;
    if (state.phase!=='combat') { socket.emit('action_error','Não é a fase de combate.'); return; }
    if (team==='blue') state.blueAttacks=attacks||[]; else state.redAttacks=attacks||[];
    state.log.unshift(`${team==='blue'?'Força Azul':'Força Vermelha'} confirmou ${(attacks||[]).length} ataque(s).`);
    if (state.blueAttacks!==null&&state.redAttacks!==null) {
      state.log.unshift('── Resolução de Combate ──');
      const combatResults = resolveCombat(state);
      const payload = { turn: state.turn, results: combatResults };
      if (room.players.blue) io.to(room.players.blue).emit('combat_result', payload);
      if (room.players.red)  io.to(room.players.red ).emit('combat_result', payload);
      const winner=checkWinner(state);
      if (winner) {
        state.winner=winner;
        state.log.unshift(`🏆 ${winner==='blue'?'Força Azul':'Força Vermelha'} VENCEU!`);
        io.to(room.players.blue).emit('game_over',{winner,state:stateFor(state,'blue')});
        io.to(room.players.red ).emit('game_over',{winner,state:stateFor(state,'red')});
        return;
      }
      nextTurn(state);
    }
    broadcast(room);
  });

  socket.on('restart', () => {
    const room=rooms.get(socket.data.roomId);
    if (!room) return;
    room.state=newGame();
    io.to(room.players.blue).emit('game_start',{team:'blue',state:stateFor(room.state,'blue')});
    io.to(room.players.red ).emit('game_start',{team:'red', state:stateFor(room.state,'red')});
  });

  socket.on('disconnect', () => {
    const {roomId,team}=socket.data; if (!roomId) return;
    const room=rooms.get(roomId); if (!room) return;
    const other=team==='blue'?room.players.red:room.players.blue;
    if (other) io.to(other).emit('opponent_disconnected');
    rooms.delete(roomId);
  });
});

server.listen(PORT, () => console.log(`Servidor em http://localhost:${PORT}`));
