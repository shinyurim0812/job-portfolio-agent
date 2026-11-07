// Native Figma nodes only. No network access and no whole-slide rasterization.
let busy = false;
let availableFamilies = [];
figma.showUI(__html__, { width: 420, height: 360, themeColors: true });

function rgb(hex) {
  return { r: parseInt(hex.slice(1,3),16)/255, g: parseInt(hex.slice(3,5),16)/255, b: parseInt(hex.slice(5,7),16)/255 };
}
function paint(hex) { return [{ type: 'SOLID', color: rgb(hex) }]; }
function decodeBase64(value) {
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  const out=[];let buffer=0,bits=0;
  for(let i=0;i<value.length;i++) {
    const n=alphabet.indexOf(value[i]);if(n<0)continue;
    buffer=(buffer<<6)|n;bits+=6;
    if(bits>=8){bits-=8;out.push((buffer>>bits)&255);}
  }
  return new Uint8Array(out);
}
function post(type, extra={}) { figma.ui.postMessage(Object.assign({type},extra)); }

async function init() {
  try {
    const fonts=await figma.listAvailableFontsAsync();
    const byFamily=new Map();
    for(const f of fonts){const a=byFamily.get(f.fontName.family)||[];a.push(f.fontName);byFamily.set(f.fontName.family,a);}
    availableFamilies=[];
    byFamily.forEach((faces,family)=>{
      const regular=faces.find(f=>/^(regular|normal|book|roman)$/i.test(f.style));
      const bold=faces.find(f=>/^bold$/i.test(f.style))||faces.find(f=>/^(semibold|semi bold|demibold)$/i.test(f.style));
      if(regular&&bold)availableFamilies.push({family,regular,bold});
    });
    const preferences=['Noto Sans KR','Pretendard','Malgun Gothic','맑은 고딕','NanumGothic','Noto Sans CJK KR'];
    availableFamilies.sort((a,b)=>{
      const x=preferences.indexOf(a.family),y=preferences.indexOf(b.family);
      return (x<0?999:x)-(y<0?999:y)||a.family.localeCompare(b.family);
    });
    if(!availableFamilies.length)throw new Error('Regular·Bold가 있는 한국어 글꼴을 설치한 뒤 다시 실행해주세요.');
    post('ready',{families:availableFamilies.map(f=>f.family),preferred:availableFamilies[0].family,count:PORTFOLIO.slides.length,width:PORTFOLIO.width,height:PORTFOLIO.height});
  } catch(error){post('error',{message:String(error.message||error)});}
}

async function createPortfolio(family) {
  if(busy)return;
  busy=true;const created=[];const previousSelection=figma.currentPage.selection.slice();
  try {
    const pair=availableFamilies.find(f=>f.family===family);
    if(!pair)throw new Error('목록에서 글꼴을 선택해주세요.');
    // Font load failure happens before any canvas mutation.
    await figma.loadFontAsync(pair.regular);
    await figma.loadFontAsync(pair.bold);
    const imageHashes={};
    for(const key of Object.keys(PORTFOLIO.assets)){
      imageHashes[key]=figma.createImage(decodeBase64(PORTFOLIO.assets[key].base64)).hash;
    }
    const page=figma.currentPage;
    const existing=page.children.slice();
    let startX=figma.viewport.center.x-PORTFOLIO.width/2;
    let startY=figma.viewport.center.y-PORTFOLIO.height/2;
    if(existing.length){
      let right=-Infinity,top=Infinity;
      for(const n of existing){const b=n.absoluteBoundingBox||{x:n.x,y:n.y,width:n.width,height:n.height};right=Math.max(right,b.x+b.width);top=Math.min(top,b.y);}
      startX=right+120;startY=top;
    }
    for(let i=0;i<PORTFOLIO.slides.length;i++) {
      const spec=PORTFOLIO.slides[i];
      const frame=figma.createFrame();created.push(frame);page.appendChild(frame);
      frame.name=String(i+1).padStart(2,'0')+' / '+spec.name;
      frame.resize(PORTFOLIO.width,PORTFOLIO.height);frame.fills=paint('#FFFFFF');frame.clipsContent=true;
      frame.x=startX+(i%3)*(PORTFOLIO.width+120);
      frame.y=startY+Math.floor(i/3)*(PORTFOLIO.height+120);
      frame.setPluginData('jobPortfolioBuilderVersion','1');
      const groups=new Map();
      for(const e of spec.elements){
        let node;
        if(e.type==='text'){
          node=figma.createText();frame.appendChild(node);
          node.fontName=e.bold?pair.bold:pair.regular;
          node.fontSize=e.size;node.lineHeight={unit:'PIXELS',value:e.lh};
          node.letterSpacing={unit:'PIXELS',value:0};node.fills=paint(e.color);
          node.textAlignHorizontal=e.align;node.textAutoResize='HEIGHT';
          node.resize(e.w,e.h);node.characters=e.text;
          if(node.height>e.h+2)throw new Error((i+1)+'페이지의 글이 영역을 넘칩니다. Noto Sans KR 또는 다른 한국어 글꼴을 선택해주세요. ('+e.name+')');
        } else if(e.type==='rect'){
          node=figma.createRectangle();frame.appendChild(node);node.resize(e.w,e.h);
          node.fills=e.fill?paint(e.fill):[];node.strokes=e.stroke?paint(e.stroke):[];
          if(e.stroke)node.strokeWeight=e.strokeWeight||1;
          if(e.radiusBR){node.topLeftRadius=0;node.topRightRadius=0;node.bottomLeftRadius=0;node.bottomRightRadius=e.radiusBR;}
        } else if(e.type==='line'){
          node=figma.createLine();frame.appendChild(node);node.resize(Math.hypot(e.w,e.h),0);node.rotation=Math.atan2(e.h,e.w)*180/Math.PI;node.strokes=paint(e.stroke);node.strokeWeight=e.weight||1;
        } else if(e.type==='image'){
          node=figma.createRectangle();frame.appendChild(node);node.resize(e.w,e.h);
          node.fills=[{type:'IMAGE',imageHash:imageHashes[e.key],scaleMode:e.fit||'FIT'}];
        } else throw new Error('지원하지 않는 요소: '+e.type);
        node.name=e.name.split('/').slice(1).join('/')||e.name;
        node.x=e.x;node.y=e.y;
        const groupName=e.name.split('/')[0];
        if(groupName!=='Background'){const a=groups.get(groupName)||[];a.push(node);groups.set(groupName,a);}
      }
      // Native groups preserve the position of their independent children.
      groups.forEach((nodes,name)=>{const g=figma.group(nodes,frame);g.name=name;});
      post('progress',{done:i+1,total:PORTFOLIO.slides.length});
    }
    page.selection=created;figma.viewport.scrollAndZoomIntoView(created);
    post('complete',{count:created.length});figma.notify(created.length+'장 생성 완료. 텍스트·도형·이미지를 각각 수정할 수 있습니다.');
  } catch(error) {
    for(const n of created){try{if(!n.removed)n.remove();}catch(_){}}
    figma.currentPage.selection=previousSelection.filter(n=>!n.removed);
    post('error',{message:String(error.message||error)});
  } finally {busy=false;}
}
figma.ui.onmessage=async message=>{
  if(message.type==='generate')await createPortfolio(message.family);
  if(message.type==='close'&&!busy)figma.closePlugin();
};
init();
