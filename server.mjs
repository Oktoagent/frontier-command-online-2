import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {WebSocketServer, WebSocket} from 'ws';
import {createClient} from 'redis';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const PORT=Math.max(1,Math.min(65535,Number(process.env.PORT)||8080));
const DATA_DIR=process.env.DATA_DIR?path.resolve(process.env.DATA_DIR):path.join(ROOT,'data'),LEADERBOARD_FILE=path.join(DATA_DIR,'player-wins.json');
const MODES={duel:{label:'1v1',players:2,teamSize:1},squad:{label:'3v3',players:6,teamSize:3},war:{label:'5v5',players:10,teamSize:5}};
const UNIT_DEFS={rifle:{cost:80,hp:125,speed:82,range:155,damage:15,rate:.62,r:10},tank:{cost:280,hp:470,speed:48,range:230,damage:46,rate:1.35,r:18},rocket:{cost:220,hp:155,speed:62,range:260,damage:54,rate:1.8,r:12,splash:70},repairer:{cost:140,hp:110,speed:76,range:115,damage:0,rate:.4,r:11,repair:24}};
const queues=new Map(Object.keys(MODES).map(k=>[k,[]])),rooms=new Map();
let unitId=1,playerWins=loadWins(),redisStore=null;

function loadWins(){try{let v=JSON.parse(fs.readFileSync(LEADERBOARD_FILE,'utf8'));return v&&typeof v==='object'?v:{}}catch{return{}}}
async function initStore(){if(!process.env.REDIS_URL)return;try{redisStore=createClient({url:process.env.REDIS_URL});redisStore.on('error',e=>console.error('Leaderboard store:',e.message));await redisStore.connect();let saved=await redisStore.get('frontier:player-wins');if(saved){let parsed=JSON.parse(saved);if(parsed&&typeof parsed==='object')playerWins=parsed}console.log('Persistent Player-Wins store connected')}catch(e){console.error('Redis unavailable, using local storage:',e.message);redisStore=null}}
function saveWins(){if(redisStore?.isReady){redisStore.set('frontier:player-wins',JSON.stringify(playerWins)).catch(e=>console.error('Leaderboard save:',e.message));return}fs.mkdirSync(DATA_DIR,{recursive:true});let tmp=LEADERBOARD_FILE+'.tmp';fs.writeFileSync(tmp,JSON.stringify(playerWins,null,2));fs.renameSync(tmp,LEADERBOARD_FILE)}
function cleanName(value){return String(value||'Commander').normalize('NFKC').replace(/[<>\u0000-\u001f]/g,'').trim().slice(0,18)||'Commander'}
function cleanId(value){let id=String(value||'').replace(/[^a-zA-Z0-9_-]/g,'').slice(0,64);return id||crypto.randomUUID()}
function send(ws,type,data={}){if(ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify({type,...data}))}
function roomBroadcast(room,type,data={}){room.players.forEach(p=>send(p.ws,type,data))}
function publicPlayer(p){return{id:p.id,profileId:p.profileId,name:p.name,team:p.team,slot:p.slot,connected:p.ws.readyState===WebSocket.OPEN}}
function leaderboard(){return Object.entries(playerWins).map(([profileId,p])=>({profileId,name:cleanName(p.name),wins:Math.max(0,+p.wins||0)})).sort((a,b)=>b.wins-a.wins||a.name.localeCompare(b.name)).slice(0,100)}
function queueSnapshot(mode){let q=queues.get(mode);q=q.filter(ws=>ws.readyState===WebSocket.OPEN&&ws.player);queues.set(mode,q);let config=MODES[mode];return{mode,label:config.label,found:q.length,required:config.players,players:q.map(ws=>({id:ws.player.id,name:ws.player.name}))}}
function publishQueue(mode){let snap=queueSnapshot(mode);queues.get(mode).forEach(ws=>send(ws,'queue_update',snap));return snap}
function leaveQueue(ws,notify=true){for(const [mode,q] of queues){let i=q.indexOf(ws);if(i>=0){q.splice(i,1);if(notify)send(ws,'queue_left',{mode});publishQueue(mode)}}ws.queueMode=null}
function allianceKey(a,b){return[a,b].sort().join('|')}
function allied(room,a,b){if(!a||!b)return false;if(a.team===b.team)return true;return room.alliances.has(allianceKey(a.owner,b.owner))}
function makeUnit(type,team,owner,x,y){let d=UNIT_DEFS[type];return{id:'u'+unitId++,type,team,owner,x,y,hp:d.hp,maxHp:d.hp,r:d.r,cd:0,dest:null,targetId:null,kills:0}}
function createRoom(mode,sockets){let config=MODES[mode],id=crypto.randomUUID(),players=sockets.map((ws,i)=>({ws,id:ws.player.id,profileId:ws.player.profileId,name:ws.player.name,team:i<config.teamSize?0:1,slot:i%config.teamSize}));let room={id,mode,config,players,units:[],bases:[{id:'base0',team:0,x:250,y:1000,hp:5200,maxHp:5200,r:62,cd:0},{id:'base1',team:1,x:2950,y:1000,hp:5200,maxHp:5200,r:62,cd:0}],resources:[900,900],alliances:new Set(),pending:new Set(),ended:false,last:Date.now(),income:0};
  for(const p of players){p.ws.roomId=id;p.ws.queueMode=null;let side=p.team===0?1:-1,b=room.bases[p.team],lane=(p.slot-(config.teamSize-1)/2)*105;room.units.push(makeUnit('rifle',p.team,p.id,b.x+side*120,b.y+lane-25),makeUnit('rifle',p.team,p.id,b.x+side*145,b.y+lane+25),makeUnit('repairer',p.team,p.id,b.x+side*95,b.y+lane+5))}
  rooms.set(id,room);roomBroadcast(room,'match_start',{roomId:id,mode,label:config.label,players:players.map(publicPlayer),state:snapshot(room)});return room}
function snapshot(room){return{roomId:room.id,mode:room.mode,serverTime:Date.now(),players:room.players.map(publicPlayer),resources:room.resources.map(Math.floor),bases:room.bases.map(b=>({...b})),units:room.units.map(u=>({...u})),alliances:[...room.alliances]}}
function findEntity(room,id){return room.units.find(u=>u.id===id)||room.bases.find(b=>b.id===id)}
function playerById(room,id){return room.players.find(p=>p.id===id)}
function unitOwner(room,u){return playerById(room,u.owner)}
function hostile(room,u,t){if(!t||t.hp<=0||u.team===t.team)return false;let a=unitOwner(room,u),owner=t.owner?unitOwner(room,t):room.players.find(p=>p.team===t.team);return !allied(room,a,owner)}
function distance(a,b){return Math.hypot(a.x-b.x,a.y-b.y)}
function nearestHostile(room,u,max=460){let best=null,bd=max;for(const t of [...room.units,...room.bases]){if(!hostile(room,u,t))continue;let d=distance(u,t)-t.r;if(d<bd){bd=d;best=t}}return best}
function applyDamage(room,target,amount,source){if(target.hp<=0)return;target.hp=Math.max(0,target.hp-amount);if(target.hp<=0&&source&&source.owner){let owner=room.units.find(u=>u.id===source.id);if(owner)owner.kills++}}
function moveToward(u,target,dt,speed){let dx=target.x-u.x,dy=target.y-u.y,d=Math.hypot(dx,dy);if(d<3){u.dest=null;return}let step=Math.min(d,speed*dt);u.x+=dx/d*step;u.y+=dy/d*step}
function updateRoom(room,dt){if(room.ended)return;room.income+=dt;if(room.income>=1){room.resources[0]+=18*room.income;room.resources[1]+=18*room.income;room.income=0}
  for(const u of room.units){if(u.hp<=0)continue;let d=UNIT_DEFS[u.type];u.cd=Math.max(0,u.cd-dt);let target=u.targetId&&findEntity(room,u.targetId);if(target&&!hostile(room,u,target))u.targetId=null,target=null;if(!target)target=nearestHostile(room,u),u.targetId=target?.id||null;
    if(u.type==='repairer'){let owner=unitOwner(room,u),repairTargets=[...room.units,...room.bases].filter(t=>t.hp>0&&t.hp<t.maxHp&&(t.team===u.team||allied(room,owner,t.owner?unitOwner(room,t):room.players.find(p=>p.team===t.team))));repairTargets.sort((a,b)=>distance(u,a)-distance(u,b));let r=repairTargets[0];if(r&&distance(u,r)<=d.range+r.r){r.hp=Math.min(r.maxHp,r.hp+d.repair*dt);u.dest=null}else if(u.dest)moveToward(u,u.dest,dt,d.speed);continue}
    if(target){let edge=distance(u,target)-target.r;if(edge<=d.range){if(u.cd<=0){u.cd=d.rate;applyDamage(room,target,d.damage,u);if(d.splash)room.units.filter(v=>hostile(room,u,v)&&v!==target&&distance(v,target)<d.splash).forEach(v=>applyDamage(room,v,d.damage*.45,u))}}else moveToward(u,target,dt,d.speed)}else if(u.dest)moveToward(u,u.dest,dt,d.speed);u.x=Math.max(30,Math.min(3170,u.x));u.y=Math.max(80,Math.min(1920,u.y))}
  room.units=room.units.filter(u=>u.hp>0);for(const b of room.bases){b.cd=Math.max(0,b.cd-dt);let fake={team:b.team,owner:room.players.find(p=>p.team===b.team)?.id,x:b.x,y:b.y},target=nearestHostile(room,fake,360);if(target&&b.cd<=0){b.cd=.55;applyDamage(room,target,24,b)}}let dead=room.bases.find(b=>b.hp<=0);if(dead)finishRoom(room,1-dead.team,'base_destroyed')}
function finishRoom(room,winnerTeam,reason){if(room.ended)return;room.ended=true;let winners=room.players.filter(p=>p.team===winnerTeam);for(const p of winners){let row=playerWins[p.profileId]||{name:p.name,wins:0};row.name=p.name;row.wins=Math.max(0,+row.wins||0)+1;playerWins[p.profileId]=row}saveWins();roomBroadcast(room,'match_end',{winnerTeam,reason,leaderboard:leaderboard()});for(const p of room.players){p.ws.roomId=null}setTimeout(()=>rooms.delete(room.id),30000)}
function handleCommand(ws,msg){let room=rooms.get(ws.roomId),player=room&&playerById(room,ws.player.id);if(!room||!player||room.ended)return;
  if(msg.type==='spawn'){let type=String(msg.unitType),d=UNIT_DEFS[type],owned=room.units.filter(u=>u.owner===player.id).length;if(!d||owned>=28||room.resources[player.team]<d.cost)return;room.resources[player.team]-=d.cost;let base=room.bases[player.team],side=player.team===0?1:-1,lane=(player.slot-(room.config.teamSize-1)/2)*100;room.units.push(makeUnit(type,player.team,player.id,base.x+side*110,base.y+lane+Math.random()*35-17));return}
  if(msg.type==='order'){let ids=Array.isArray(msg.unitIds)?msg.unitIds.slice(0,40):[],x=Math.max(30,Math.min(3170,+msg.x||0)),y=Math.max(80,Math.min(1920,+msg.y||0)),target=findEntity(room,String(msg.targetId||''));for(const id of ids){let u=room.units.find(v=>v.id===id&&v.owner===player.id);if(!u)continue;u.dest={x,y};u.targetId=target&&hostile(room,u,target)?target.id:null}return}
  if(msg.type==='alliance_request'){let target=playerById(room,String(msg.targetPlayerId));if(!target||target.id===player.id||room.alliances.has(allianceKey(player.id,target.id)))return;room.pending.add(player.id+'>'+target.id);send(target.ws,'alliance_request',{from:publicPlayer(player)});send(ws,'notice',{message:'ALLIANCE REQUEST SENT'});return}
  if(msg.type==='alliance_accept'){let from=playerById(room,String(msg.fromPlayerId)),pending=from&&from.id+'>'+player.id;if(!from||!room.pending.has(pending))return;room.pending.delete(pending);room.alliances.add(allianceKey(from.id,player.id));roomBroadcast(room,'alliance_update',{alliances:[...room.alliances],message:`${from.name} + ${player.name}`});return}
  if(msg.type==='alliance_reject'){room.pending.delete(String(msg.fromPlayerId)+'>'+player.id);return}
  if(msg.type==='alliance_break'){let target=playerById(room,String(msg.targetPlayerId));if(target){room.alliances.delete(allianceKey(player.id,target.id));roomBroadcast(room,'alliance_update',{alliances:[...room.alliances],message:`${player.name} broke an alliance`})}}
}

function requestPath(req){
  const raw=String(req.url||'/');
  try{return new URL(raw,'http://render.local').pathname.replace(/\/+$/,'')||'/'}
  catch{return raw.split('?')[0].replace(/\/+$/,'')||'/'}
}
function statusPayload(){return {ok:true,build:'32.0.0',rooms:rooms.size,queues:Object.fromEntries([...queues].map(([k,v])=>[k,v.length])),time:new Date().toISOString()}}
const server=http.createServer((req,res)=>{
  const pathname=requestPath(req);
  console.log(`[HTTP] ${req.method||'GET'} ${pathname}`);
  res.setHeader('x-frontier-build','32.0.0');
  if(['/health','/healthz','/api/status'].includes(pathname)){
    res.writeHead(200,{'content-type':'application/json; charset=utf-8','cache-control':'no-store'});
    return res.end(req.method==='HEAD'?'':JSON.stringify(statusPayload()));
  }
  const file=pathname==='/'?'frontier-command.html':pathname.slice(1);
  if(file!=='frontier-command.html'){
    res.writeHead(404,{'content-type':'text/plain; charset=utf-8','cache-control':'no-store'});
    return res.end(`Frontier Command Build 32: route not found (${pathname})`);
  }
  fs.readFile(path.join(ROOT,file),(err,data)=>{
    if(err){res.writeHead(404,{'content-type':'text/plain; charset=utf-8'});return res.end('Frontier Command: game file not found')}
    res.writeHead(200,{'content-type':'text/html; charset=utf-8','cache-control':'no-store'});
    res.end(req.method==='HEAD'?'':data);
  });
});
const wss=new WebSocketServer({server,path:'/ws'});
wss.on('connection',ws=>{ws.clientId=crypto.randomUUID();ws.rate={at:Date.now(),count:0};send(ws,'connected',{clientId:ws.clientId,modes:MODES});ws.on('message',raw=>{let now=Date.now();if(now-ws.rate.at>1000)ws.rate={at:now,count:0};if(++ws.rate.count>80)return;let msg;try{msg=JSON.parse(String(raw))}catch{return}if(msg.type==='hello'){ws.player={id:ws.clientId,profileId:cleanId(msg.profileId),name:cleanName(msg.name)};send(ws,'hello',{player:ws.player,leaderboard:leaderboard(),modes:MODES});return}if(msg.type==='leaderboard'){send(ws,'leaderboard',{leaderboard:leaderboard()});return}if(msg.type==='queue_join'){let mode=String(msg.mode);if(!ws.player||!MODES[mode]||ws.roomId)return;leaveQueue(ws,false);let q=queues.get(mode);if(!q.includes(ws))q.push(ws);ws.queueMode=mode;let snap=publishQueue(mode);if(snap.found===snap.required){let sockets=q.splice(0,snap.required);publishQueue(mode);createRoom(mode,sockets)}return}if(msg.type==='queue_leave'){leaveQueue(ws);return}handleCommand(ws,msg)});ws.on('close',()=>{leaveQueue(ws,false);let room=rooms.get(ws.roomId);if(room&&!room.ended){roomBroadcast(room,'player_disconnected',{playerId:ws.player?.id});let player=playerById(room,ws.player?.id),team=player?.team;if(team!==undefined&&!room.players.some(p=>p.team===team&&p.ws.readyState===WebSocket.OPEN))finishRoom(room,1-team,'team_disconnected')}})});
setInterval(()=>{let now=Date.now();for(const room of rooms.values()){let dt=Math.min(.2,(now-room.last)/1000);room.last=now;updateRoom(room,dt);if(!room.ended)roomBroadcast(room,'state',{state:snapshot(room)})}},100);
await initStore();
server.listen(PORT,'0.0.0.0',()=>console.log(`Frontier Command Online: http://0.0.0.0:${PORT}`));
