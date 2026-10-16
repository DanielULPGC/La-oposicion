// Escena realista de «El tribunal» (Three.js r170).
// Se empaqueta con esbuild en un script clásico (IIFE) que se incrusta en la página.
// Usa variables globales de la página: $, paused, setView, setAudience, setStation,
// ST, S, showTab, updateAudience, initProcedural.
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RGBELoader } from "three/examples/jsm/loaders/RGBELoader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { GTAOPass } from "three/examples/jsm/postprocessing/GTAOPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";

window.THREE = THREE;   // para la versión simplificada de respaldo

function b64ToBuffer(b64){
  const bin = atob(b64), n = bin.length, u8 = new Uint8Array(n);
  for(let i=0;i<n;i++) u8[i] = bin.charCodeAt(i);
  return u8.buffer;
}
async function readStream(res, cb){
  const total = +res.headers.get("content-length") || 0;
  if(!res.body || !total || !cb) return res;
  const reader = res.body.getReader(), chunks = []; let got = 0;
  for(;;){ const {done, value} = await reader.read(); if(done) break; chunks.push(value); got += value.length; cb({loaded:got, total}); }
  return new Response(new Blob(chunks));
}
// Binario publicado junto a la página: variable incrustada, fichero binario o copia en base64 (.txt)
async function loadBinary(name, globalName, cb){
  if(window[globalName]) return b64ToBuffer(window[globalName]);
  try{ const r = await fetch(name); if(r.ok) return (await readStream(r, cb)).arrayBuffer(); }catch(e){}
  const r2 = await fetch(name + ".txt");
  if(!r2.ok) throw new Error("No se encuentra " + name);
  return b64ToBuffer((await (await readStream(r2, cb)).text()).trim());
}

window.initRealistic = function initRealistic(){
  const canvas = $("#scene");
  const stage = canvas.parentElement;
  const Q = {
    alta:{pr:2, shadow:2048, post:true, dust:true},
    media:{pr:1.5, shadow:1024, post:false, dust:true},
    baja:{pr:1, shadow:0, post:false, dust:false}
  };
  let qName = (()=>{ try{ const v = localStorage.getItem("tribunal-q"); if(Q[v]) return v; }catch(e){}
    return matchMedia("(max-width:820px)").matches ? "media" : "alta"; })();
  let renderer;
  try{ renderer = new THREE.WebGLRenderer({canvas, antialias:true, powerPreference:"high-performance"}); }
  catch(e){ $("#nogl").hidden = false; canvas.hidden = true; $("#loading").hidden = true; return; }
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 0.66;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0d1014);
  const camera = new THREE.PerspectiveCamera(46, 1, 0.05, 80);
  const C = new THREE.Vector3(0, 0, -4.4);
  let alive = true;

  // Sol dinámico: la misma dirección e intensidad que en el horneado
  // Blender: fuerza 4 deja una superficie blanca en 4; Three divide por π, de ahí el factor
  const sun = new THREE.DirectionalLight(new THREE.Color(1.0, 0.89, 0.72), 4.0 * Math.PI);
  sun.position.set(7, 18, -28); sun.target.position.set(0, 0, -1);
  scene.add(sun, sun.target);
  Object.assign(sun.shadow.camera, {left:-21, right:21, top:21, bottom:-21, near:6, far:75});
  sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.025;
  const spot = new THREE.SpotLight(0xffe9c8, 9, 14, 0.33, 0.7, 2);
  spot.position.set(1.6, 6.6, 1.2); spot.target.position.set(0, 1.1, -0.8);
  scene.add(spot, spot.target);

  // Posprocesado (calidad alta): oclusión ambiental, resplandor y salida
  let composer = null, gtao = null;
  function buildComposer(w, h){
    if(composer){ composer.dispose(); composer = null; }
    const rt = new THREE.WebGLRenderTarget(w, h, {type:THREE.HalfFloatType, samples:4});
    composer = new EffectComposer(renderer, rt);
    composer.addPass(new RenderPass(scene, camera));
    gtao = new GTAOPass(scene, camera, w, h);
    gtao.updateGtaoMaterial({radius:0.45, distanceExponent:1.5, thickness:1.0, scale:1.0, samples:12});
    gtao.blendIntensity = 0.85;
    // Los haces y el polvo no deben generar oclusión ambiental
    const gtaoRender = gtao.render.bind(gtao);
    gtao.render = (...a)=>{ const v1 = beams.visible, v2 = dust.visible; beams.visible = false; dust.visible = false; gtaoRender(...a); beams.visible = v1; dust.visible = v2; };
    composer.addPass(gtao);
    composer.addPass(new UnrealBloomPass(new THREE.Vector2(w, h), 0.28, 0.5, 4.0));
    composer.addPass(new OutputPass());
  }
  function resize(){
    const r = stage.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    camera.aspect = r.width / Math.max(1, r.height);
    camera.fov = camera.aspect < 1 ? 64 : camera.aspect < 1.4 ? 56 : 48;
    camera.updateProjectionMatrix();
    if(Q[qName].post){
      const pr = renderer.getPixelRatio();
      const w = Math.round(r.width*pr), h = Math.round(r.height*pr);
      if(!composer) buildComposer(w, h); else { composer.setPixelRatio(1); composer.setSize(w, h); }
    }
  }
  function applyQuality(){
    const q = Q[qName];
    renderer.setPixelRatio(Math.min(devicePixelRatio, q.pr));
    renderer.shadowMap.enabled = q.shadow > 0;
    sun.castShadow = q.shadow > 0;
    sun.visible = q.shadow > 0;   // sin sombras, el sol atravesaría los muros
    if(q.shadow){ sun.shadow.mapSize.set(q.shadow, q.shadow); if(sun.shadow.map){ sun.shadow.map.dispose(); sun.shadow.map = null; } }
    if(!q.post && composer){ composer.dispose(); composer = null; }
    scene.traverse(o=>{ if(o.material) [].concat(o.material).forEach(m=>m.needsUpdate = true); });
    dust.visible = q.dust;
    resize();
  }
  const qsel = $("#quality");
  qsel.value = qName; qsel.disabled = false;
  qsel.addEventListener("change", ()=>{ qName = qsel.value; try{ localStorage.setItem("tribunal-q", qName); }catch(e){} applyQuality(); });

  // Haces de luz y motas de polvo en las ventanas del fondo
  const into = sun.position.clone().sub(sun.target.position).normalize().negate();
  const gc = document.createElement("canvas"); gc.width = 64; gc.height = 256;
  const gx = gc.getContext("2d");
  const gv = gx.createLinearGradient(0, 0, 0, 256);
  gv.addColorStop(0, "rgba(255,226,176,1)"); gv.addColorStop(0.6, "rgba(255,226,176,.45)"); gv.addColorStop(1, "rgba(255,226,176,0)");
  gx.fillStyle = gv; gx.fillRect(0, 0, 64, 256);
  const gh = gx.createLinearGradient(0, 0, 64, 0);
  gh.addColorStop(0, "rgba(0,0,0,1)"); gh.addColorStop(0.2, "rgba(0,0,0,0)"); gh.addColorStop(0.8, "rgba(0,0,0,0)"); gh.addColorStop(1, "rgba(0,0,0,1)");
  gx.globalCompositeOperation = "destination-out"; gx.fillStyle = gh; gx.fillRect(0, 0, 64, 256);
  const beamTex = new THREE.CanvasTexture(gc); beamTex.colorSpace = THREE.SRGBColorSpace;
  const beamMat = new THREE.MeshBasicMaterial({map:beamTex, transparent:true, opacity:0.035, blending:THREE.AdditiveBlending,
    depthWrite:false, side:THREE.DoubleSide, toneMapped:false});
  const WINS = [-8.6, -4.6, 4.6, 8.6], SILL = 2.95, TOP = 6.25, WW = 1.6, BACKZ = -7.66, BLEN = 9.5;
  const beams = new THREE.Group(); scene.add(beams);
  WINS.forEach(x=>{
    const c = [[x-WW/2,SILL],[x+WW/2,SILL],[x+WW/2,TOP],[x-WW/2,TOP]].map(([a,b])=>new THREE.Vector3(a,b,BACKZ));
    const far = c.map(v=>v.clone().addScaledVector(into, BLEN));
    const pos = [], uv = [];
    for(let i=0;i<4;i++){
      const a = c[i], b = c[(i+1)%4], a2 = far[i], b2 = far[(i+1)%4];
      [[a,0,0],[b,1,0],[b2,1,1],[a,0,0],[b2,1,1],[a2,0,1]].forEach(([v,u,w])=>{ pos.push(v.x,v.y,v.z); uv.push(u,1-w); });
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
    beams.add(new THREE.Mesh(g, beamMat));
  });
  const ND = 700, dpos = new Float32Array(ND*3), dseed = new Float32Array(ND);
  for(let i=0;i<ND;i++){
    const x = WINS[i % 4] + (Math.random()-0.5)*WW, y = SILL + Math.random()*(TOP-SILL), t = Math.random()*BLEN*0.85;
    dpos[i*3] = x + into.x*t; dpos[i*3+1] = y + into.y*t; dpos[i*3+2] = BACKZ + into.z*t; dseed[i] = Math.random()*6.28;
  }
  const dustG = new THREE.BufferGeometry(); dustG.setAttribute("position", new THREE.BufferAttribute(dpos, 3));
  const dust = new THREE.Points(dustG, new THREE.PointsMaterial({color:0xffe6bd, size:0.012, transparent:true, opacity:0.4, depthWrite:false, toneMapped:false}));
  scene.add(dust);

  // Cámara: vistas, órbita, rueda y pellizco
  const VIEWS = {
    sala:{r:10, yaw:0.3, pitch:0.36, look:new THREE.Vector3(0, 1.2, -3.6)},
    opositor:{r:4.6, yaw:0.62, pitch:0.22, look:new THREE.Vector3(0, 1.4, -1.2)},
    tribunal:{r:5.6, yaw:-0.08, pitch:0.18, look:new THREE.Vector3(0, 1.2, -5.0)}
  };
  const cam = {r:10, yaw:0.3, pitch:0.36, look:VIEWS.sala.look.clone()}, goal = {r:10, yaw:0.3, pitch:0.36, look:VIEWS.sala.look.clone()};
  setView = name => {
    const v = VIEWS[name]; goal.r = v.r; goal.yaw = v.yaw; goal.pitch = v.pitch; goal.look.copy(v.look);
    document.querySelectorAll("[data-view]").forEach(b=>b.setAttribute("aria-pressed", b.dataset.view===name));
    if(paused){ cam.r = goal.r; cam.yaw = goal.yaw; cam.pitch = goal.pitch; cam.look.copy(goal.look); }
  };
  document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click", ()=>setView(b.dataset.view)));
  const ptrs = new Map(); let drag = null, pinch = null;
  canvas.addEventListener("pointerdown", e=>{
    ptrs.set(e.pointerId, {x:e.clientX, y:e.clientY}); canvas.setPointerCapture(e.pointerId);
    if(ptrs.size === 1) drag = {x:e.clientX, y:e.clientY, yaw:goal.yaw, pitch:goal.pitch};
    if(ptrs.size === 2){ const [a,b] = [...ptrs.values()]; pinch = {d:Math.hypot(a.x-b.x, a.y-b.y), r:goal.r}; drag = null; }
  });
  canvas.addEventListener("pointermove", e=>{
    if(!ptrs.has(e.pointerId)) return;
    ptrs.set(e.pointerId, {x:e.clientX, y:e.clientY});
    if(pinch && ptrs.size === 2){ const [a,b] = [...ptrs.values()]; goal.r = THREE.MathUtils.clamp(pinch.r * pinch.d / Math.max(20, Math.hypot(a.x-b.x, a.y-b.y)), 2.2, 10.5); }
    else if(drag){
      goal.yaw = THREE.MathUtils.clamp(drag.yaw - (e.clientX-drag.x)*0.005, -1.05, 1.05);
      goal.pitch = THREE.MathUtils.clamp(drag.pitch + (e.clientY-drag.y)*0.004, 0.04, 0.85);
    }
    if(paused){ cam.yaw = goal.yaw; cam.pitch = goal.pitch; cam.r = goal.r; }
  });
  const up = e=>{ ptrs.delete(e.pointerId); if(ptrs.size < 2) pinch = null; if(ptrs.size === 0) drag = null; };
  canvas.addEventListener("pointerup", up); canvas.addEventListener("pointercancel", up);
  canvas.addEventListener("wheel", e=>{ e.preventDefault(); goal.r = THREE.MathUtils.clamp(goal.r * (1 + Math.sign(e.deltaY)*0.08), 2.2, 10.5); if(paused) cam.r = goal.r; }, {passive:false});
  function placeCamera(){
    const cp = Math.cos(cam.pitch);
    const p = new THREE.Vector3(Math.sin(cam.yaw)*cp, Math.sin(cam.pitch), Math.cos(cam.yaw)*cp).multiplyScalar(cam.r).add(cam.look);
    const dx = p.x - C.x, dz = p.z - C.z, dist = Math.hypot(dx, dz);
    if(dist > 11.2){ p.x = C.x + dx*11.2/dist; p.z = C.z + dz*11.2/dist; }
    p.y = Math.min(p.y, 6.5); p.z = Math.max(p.z, -7.3);
    camera.position.copy(p); camera.lookAt(cam.look);
  }

  // Carga
  const loadingBox = $("#loading"), lbar = $("#lbar"), ltext = $("#ltext");
  const onProgress = ev=>{ if(ev && ev.total){ const f = ev.loaded/ev.total; lbar.style.width = Math.round(f*100) + "%"; ltext.textContent = `Cargando la sala… ${Math.round(f*100)} %`; } };
  const fail = err=>{
    console.warn("No se pudo cargar la sala realista:", err);
    alive = false; renderer.dispose();
    const fresh = canvas.cloneNode(false); canvas.replaceWith(fresh);
    loadingBox.hidden = true; qsel.disabled = true;
    initProcedural(); updateAudience(); setStation(ST.n); showTab(S.tab||0);
  };

  // Entorno de reflejos: panorama renderizado de la propia sala
  loadBinary("sala_env.hdr", "ENV_HDR_B64").then(buf=>{
    const url = URL.createObjectURL(new Blob([buf]));
    new RGBELoader().load(url, tex=>{
      tex.mapping = THREE.EquirectangularReflectionMapping;
      const pm = new THREE.PMREMGenerator(renderer);
      scene.environment = pm.fromEquirectangular(tex).texture;
      tex.dispose(); pm.dispose(); URL.revokeObjectURL(url);
    });
  }).catch(e=>console.warn("Sin entorno de reflejos", e));

  const G = {}; let pen, sword, flames = [], fireLight, aud = null, armJ = null; const joints = [];
  const onLoad = gltf=>{
    const root = gltf.scene;
    const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    // Lightmaps horneados en Blender
    const carrier = root.getObjectByName("LM_Carrier");
    let lmInfo = null; const lmTex = {};
    if(carrier){
      lmInfo = JSON.parse(carrier.userData.lmScale || "{}");
      carrier.traverse(o=>{ if(o.isMesh) [].concat(o.material).forEach(m=>{
        const tag = m.name === "LM_A" ? "A" : m.name === "LM_B" ? "B" : null;
        if(tag && m.map){ const t = m.map; t.channel = 1; t.colorSpace = THREE.SRGBColorSpace; t.needsUpdate = true; lmTex[tag] = t; }
      }); });
      carrier.visible = false;
    }
    const groupOf = o=>{
      if(!lmInfo) return null;
      for(let p = o; p; p = p.parent){
        if((lmInfo.groupA||[]).includes(p.name)) return "A";
        if((lmInfo.groupB||[]).includes(p.name)) return "B";
      }
      return null;
    };
    const lmCache = new Map();
    root.traverse(o=>{
      if(!o.isMesh) return;
      o.castShadow = true; o.receiveShadow = true;
      const g = groupOf(o);
      const mats = [].concat(o.material).map(m=>{
        m.envMapIntensity = 1.0;
        ["map","normalMap"].forEach(k=>{ if(m[k]) m[k].anisotropy = aniso; });
        if(m.name === "Paño" && m.normalScale) m.normalScale.set(0.15, 0.15);
        if(m.name === "Vidrio"){ Object.assign(m, {transparent:true, opacity:0.14, depthWrite:false, roughness:0.04, metalness:0, envMapIntensity:1.6}); o.castShadow = false; }
        if(m.name === "Cielo"){ m.emissiveIntensity = 6.0; m.toneMapped = true; o.castShadow = false; o.receiveShadow = false; }
        if(m.name === "Globo"){ m.emissiveIntensity = 6.0; o.castShadow = false; }
        if(m.name === "Llama"){ Object.assign(m, {emissiveIntensity:8, transparent:true, opacity:0.9}); o.castShadow = false; }
        if(g && lmTex[g] && o.geometry.attributes.uv1){
          const key = m.uuid + g;
          if(!lmCache.has(key)){
            const c = m.clone();
            c.lightMap = lmTex[g]; c.lightMapIntensity = Math.PI * (lmInfo[g] || 1);
            c.envMapIntensity = 0.25;
            lmCache.set(key, c);
          }
          return lmCache.get(key);
        }
        return m;
      });
      o.material = Array.isArray(o.material) ? mats : mats[0];
    });
    scene.add(root);
    ["ST2","ST3","ST4","ST5"].forEach(k=>{ G[k] = root.getObjectByName(k); if(G[k]) G[k].visible = false; });
    pen = root.getObjectByName("Pen"); sword = root.getObjectByName("Sword");
    root.traverse(o=>{ if(/^Flame\d/.test(o.name)){ flames.push(o); o.userData.k = Math.random()*6; o.userData.s0 = o.scale.clone(); } });
    const ship = root.getObjectByName("Ship1");
    if(ship){ fireLight = new THREE.PointLight(0xff7a30, 0, 3, 2); fireLight.position.set(0, 0.25, 0); ship.add(fireLight); }

    // Público instanciado: diez plantillas de postura, una InstancedMesh por plantilla y material
    root.updateMatrixWorld(true);
    const tplRoot = root.getObjectByName("AudienceTemplates");
    const tpls = [];
    for(let i=0;i<10;i++){ const t = root.getObjectByName("Aud"+i); if(t) tpls.push(t); }
    const seatsNode = root.getObjectByName("Seats");
    if(tplRoot && tpls.length && seatsNode && seatsNode.userData.seats){
      tplRoot.visible = false;
      let seats = JSON.parse(seatsNode.userData.seats);
      let rnd = 7; const rand = ()=>((rnd = (rnd*16807) % 2147483647) / 2147483647);
      seats = seats.map(s=>({s, k:s[4] + rand()*1.6})).sort((a,b)=>a.k-b.k).map(o=>o.s);
      const N = seats.length;
      // pesos de cada postura (la mano alzada, rara)
      const W = [3,2,1.6,2,2,2,2,0.35,1.4,1.8].slice(0, tpls.length), Wsum = W.reduce((a,b)=>a+b,0);
      const pose = seats.map(()=>{ let r = rand()*Wsum, k = 0; while(k < W.length-1 && (r -= W[k]) > 0) k++; return k; });
      const top = [0x5b6470,0x6f5a48,0x44604f,0x7d6a52,0x55496b,0x6c7883,0x8a6a42,0x3f4b5a,0x7a4a42,0x5d6b3e,0x8c8378,0x4d5d6e];
      const bot = [0x2b2f36,0x3a3229,0x23282e,0x45403a,0x2f3a44,0x1f1f22,0x4a3b30,0x363a2c];
      const ph = new Float32Array(N*3); for(let i=0;i<N*3;i++) ph[i] = rand()*6.283;
      const delay = new Float32Array(N); for(let i=0;i<N;i++) delay[i] = seats[i][4]*0.16 + rand()*0.3;
      const meshes = [];
      tpls.forEach((tpl, k)=>{
        const ids = []; for(let i=0;i<N;i++) if(pose[i] === k) ids.push(i);
        if(!ids.length) return;
        tpl.traverse(p=>{
          if(!p.isMesh) return;
          const mat = p.material.clone();
          const im = new THREE.InstancedMesh(p.geometry, mat, ids.length);
          im.castShadow = true; im.receiveShadow = true; im.frustumCulled = false;
          im.userData.local = p.matrixWorld.clone(); im.userData.ids = ids;
          const pal = mat.name === "RopaPublico" ? top : mat.name === "PantalonPublico" ? bot : null;
          if(pal){ mat.color.setRGB(1,1,1); ids.forEach((i, j)=>im.setColorAt(j, new THREE.Color(pal[(i*7 + (pal === bot ? 3 : 0)) % pal.length]))); }
          scene.add(im); meshes.push(im);
        });
      });
      aud = {seats, meshes, t:new Float32Array(N), target:6, dirty:true, ph, delay, react:-99};
    }
    // Figuras con articulaciones animables (pivotes exportados desde Blender)
    const HEADS = {
      Presidente_Cabeza: {yaw:[-0.35,0.35], pitch:[-0.06,0.12], every:[2.5,6]},
      Vocal_Cabeza:      {yaw:[-0.15,0.2],  pitch:[-0.38,0.04], every:[2,5]},
      VocalJoven_Cabeza: {yaw:[-0.45,0.3],  pitch:[-0.08,0.1],  every:[3,7]},
      Opositor_Cabeza:   {yaw:[-0.65,0.65], pitch:[-0.12,0.08], every:[1.8,4.5]},
    };
    Object.entries(HEADS).forEach(([n, cfg])=>{
      const o = root.getObjectByName(n);
      if(o) joints.push({o, q0:o.quaternion.clone(), cfg, y:0, p:0, ty:0, tp:0, next:0});
    });
    armJ = root.getObjectByName("Opositor_Brazo");
    if(armJ) armJ.userData.q0 = armJ.quaternion.clone();
    setAudience = f=>{
      if(!aud) return;
      aud.target = Math.round(6 + f*(aud.seats.length - 6));
      $("#aud").textContent = aud.target;
      if(paused){ for(let i=0;i<aud.t.length;i++) aud.t[i] = i < aud.target ? 1 : 0; aud.dirty = true; }
    };
    setStation = n=>{ ["ST2","ST3","ST4","ST5"].forEach(k=>{ if(G[k]) G[k].visible = (k === "ST"+n); }); };
    loadingBox.hidden = true;
    applyQuality();
    updateAudience(); setStation(ST.n);
    if(aud && paused){ for(let i=0;i<aud.t.length;i++) aud.t[i] = i < aud.target ? 1 : 0; aud.dirty = true; }
  };
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  loadBinary("sala.glb", "SALA_GLB_B64", onProgress)
    .then(buf=>loader.parse(buf, "", onLoad, fail))
    .catch(fail);

  const m4 = new THREE.Matrix4(), m5 = new THREE.Matrix4(), q4 = new THREE.Quaternion(), qa = new THREE.Quaternion(), e3 = new THREE.Euler(),
        v3 = new THREE.Vector3(), s3 = new THREE.Vector3(), yAx = new THREE.Vector3(0,1,0), xAx = new THREE.Vector3(1,0,0);
  window.reactAudience = ()=>{ if(aud && !paused) aud.react = clock.elapsedTime; };
  function updateAudienceMeshes(dt, t){
    if(!aud) return;
    let changed = aud.dirty || !paused;
    for(let i=0;i<aud.t.length;i++){
      const want = i < aud.target ? 1 : 0;
      if(!paused && aud.t[i] !== want){ aud.t[i] += (want - aud.t[i]) * Math.min(1, dt*5); if(Math.abs(aud.t[i]-want) < 0.01) aud.t[i] = want; changed = true; }
    }
    if(!changed) return;
    const live = !paused, N = aud.t.length; const per = aud.per || (aud.per = new Float32Array(N*16));
    // matriz de cada asiento (postura viva: balanceo, respiración y reacción en ola)
    for(let i=0;i<N;i++){
      const s = aud.seats[i], k = Math.max(0.0001, aud.t[i]), p = aud.ph;
      let lean = 0, sway = 0, br = 1;
      if(live){
        sway = 0.035*Math.sin(t*0.31 + p[i*3]) + 0.015*Math.sin(t*0.83 + p[i*3+1]);
        lean = 0.02*Math.sin(t*0.21 + p[i*3+2]);
        br = 1 + 0.006*Math.sin(t*1.6 + p[i*3]);
        const tau = t - aud.react - aud.delay[i];
        if(tau > 0 && tau < 1.6) lean += 0.075*Math.sin(Math.PI*tau/1.6);
      }
      v3.set(s[0], s[1] - (1-k)*0.3, s[2]);
      q4.setFromAxisAngle(yAx, s[3]); qa.setFromEuler(e3.set(lean, sway, 0, "YXZ")); q4.multiply(qa);
      s3.set(k, k*br, k);
      m4.compose(v3, q4, s3).toArray(per, i*16);
    }
    aud.meshes.forEach(im=>{
      const ids = im.userData.ids;
      for(let j=0;j<ids.length;j++){ m4.fromArray(per, ids[j]*16).multiply(im.userData.local); im.setMatrixAt(j, m4); }
      im.instanceMatrix.needsUpdate = true;
      if(aud.dirty && im.instanceColor) im.instanceColor.needsUpdate = true;
    });
    aud.dirty = false;
  }
  // Cabezas que miran alrededor y gesto del opositor
  const rr = (a,b)=>a + Math.random()*(b-a);
  function updateJoints(dt, t){
    joints.forEach(j=>{
      if(t > j.next){ j.ty = rr(...j.cfg.yaw); j.tp = rr(...j.cfg.pitch); j.next = t + rr(...j.cfg.every); }
      const k = 1 - Math.pow(0.04, dt);
      j.y += (j.ty - j.y)*k; j.p += (j.tp - j.p)*k;
      qa.setFromEuler(e3.set(j.p + 0.012*Math.sin(t*1.3 + j.next), j.y, 0, "YXZ"));
      j.o.quaternion.copy(j.cfg.q0 || j.q0).multiply(qa);
    });
    if(armJ){
      const g = Math.max(0, Math.sin(t*0.45)), a = 0.13*g*Math.sin(t*2.6), b = 0.05*Math.sin(t*0.9);
      qa.setFromEuler(e3.set(a, 0, b, "XYZ"));
      armJ.quaternion.copy(armJ.userData.q0).multiply(qa);
    }
  }

  new ResizeObserver(resize).observe(stage); applyQuality();
  const clock = new THREE.Clock();
  function frame(){
    if(!alive) return;
    const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
    if(!paused){
      const k = 1 - Math.pow(0.02, dt);
      cam.r += (goal.r-cam.r)*k; cam.yaw += (goal.yaw-cam.yaw)*k; cam.pitch += (goal.pitch-cam.pitch)*k; cam.look.lerp(goal.look, k);
      if(dust.visible){
        const p = dustG.attributes.position;
        for(let i=0;i<ND;i++){ p.setX(i, p.getX(i) + Math.sin(t*0.4 + dseed[i])*dt*0.03); p.setY(i, p.getY(i) + Math.cos(t*0.3 + dseed[i])*dt*0.02); }
        p.needsUpdate = true;
      }
      updateJoints(dt, t);
      if(sword && G.ST3 && G.ST3.visible) sword.rotation.y += dt*0.45;
      if(flames.length && G.ST4 && G.ST4.visible){
        flames.forEach(f=>{ const s = 0.75 + 0.3*Math.sin(t*9 + f.userData.k) + 0.15*Math.sin(t*23 + f.userData.k); const s0 = f.userData.s0; f.scale.set(s0.x, s0.y*s, s0.z); });
        if(fireLight) fireLight.intensity = 3 + Math.sin(t*11);
      } else if(fireLight) fireLight.intensity = 0;
    }
    updateAudienceMeshes(dt, t);
    placeCamera();
    if(composer && Q[qName].post) composer.render(); else renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  frame();
};
