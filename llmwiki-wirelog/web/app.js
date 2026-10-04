'use strict';
let config,history=[],busy=false;
const $=id=>document.getElementById(id);
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
const samples=['ledger 지연 때 어떤 서비스를 점검해야 하나요? notify의 오류가 결제 취소로 이어지나요?','결제 서비스 담당 팀과 현재 당직자를 알려줘.','25분과 42분은 각각 무슨 뜻이야?','S2에서 S3로 바꾸면 영향 후보가 어떻게 달라지나요?','대사 큐를 지금 중지해도 되나요?'];
samples.forEach(s=>{const b=el('button',s,'example');b.type='button';b.onclick=()=>{$('question').value=s;$('question').focus();};$('examples').append(b);});
async function api(path,options={}){const r=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-Local-Token':config?.token||'',...(options.headers||{})}});const v=await r.json();if(!r.ok)throw Error(v.error||'요청 실패');return v;}
function answerView(result,container){
 const a=el('div',undefined,'answer');a.append(el('div',`${result.snapshot} · PyreWire 1.1.2 · ${result.tool_calls.length}회 도구 조회`,'meta'));
 const evidenceBox=el('details',undefined,'evidence');evidenceBox.append(el('summary','원문·관계 근거 확인'));
 const cards={};const used=new Set(result.answer.claims.flatMap(c=>c.citations));
 Object.entries(result.evidence).forEach(([id,e])=>{if(!used.has(id))return;const card=el('section');cards[id]=card;
  card.append(el('h4',`${id} · ${e.kind==='graph'?`${e.snapshot} 관계 조회 (${e.action})`:`${e.doc_id} ${e.section}`}`));
  card.append(el('p',e.kind==='graph'?e.scope:`${e.status} · data/${e.path}`,'meta'));
  card.append(el('pre',e.kind==='graph'?JSON.stringify({rows:e.rows,paths:e.paths,facts:e.facts},null,2):e.quote));evidenceBox.append(card);
 });
 result.answer.claims.forEach(c=>{const p=el('p',undefined,'claim');p.append(el('span',({fact:'사실',inference:'해석',proposal:'제안'})[c.kind],'tag'),document.createTextNode(c.text));c.citations.forEach(id=>{const b=el('button',id,'citation');b.onclick=()=>{evidenceBox.open=true;cards[id].scrollIntoView({behavior:'smooth',block:'center'});};p.append(b);});a.append(p);});
 if(result.answer.unknowns.length){const box=el('div',undefined,'unknowns');box.append(el('strong','미확인·추가 확인'));const ul=el('ul');result.answer.unknowns.forEach(s=>ul.append(el('li',s)));box.append(ul);a.append(box);}
 if(result.answer.follow_up)a.append(el('p',result.answer.follow_up));
 if(used.size)a.append(evidenceBox);
 const trace=el('details',undefined,'trace');trace.append(el('summary','검색·질의 과정'));result.tool_calls.forEach(c=>trace.append(el('p',`${c.tool} ${JSON.stringify(c.arguments)} → ${c.output.status}`)));a.append(trace);
 a.append(el('p',`실행 기록: runs/${result.run_id} · 인용과 구조 검증 완료. 의미 판단은 원문과 대조하세요.`,'meta'));
 const download=el('button','답변·근거 JSON 저장','download');download.onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const link=el('a');link.href=url;link.download='llmwiki-answer.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};a.append(download);container.append(a);
}
$('ask').onsubmit=async event=>{event.preventDefault();if(busy||!config)return;const question=$('question').value.trim();if(!question)return;busy=true;$('submit').disabled=true;$('reset').disabled=true;$('snapshot').disabled=true;$('welcome')?.remove();const message=el('article',undefined,'message');message.append(el('div',question,'question'));$('messages').append(message);$('question').value='';$('progress').textContent='질문을 접수하고 있습니다…';try{
 const {job_id}=await api('/api/ask',{method:'POST',body:JSON.stringify({question,snapshot:$('snapshot').value,history})});
 for(;;){const job=await api(`/api/jobs/${job_id}`);$('progress').textContent=job.events.at(-1)||'대기 중…';if(job.status==='success'){answerView(job.result,message);history.push({question:question.slice(0,1000),answer:JSON.stringify(job.result.answer).slice(0,3500)});history=history.slice(-3);break;}if(job.status==='error')throw Error(job.message);await new Promise(r=>setTimeout(r,1200));}
 }catch(err){message.append(el('div',err.message,'error'));$('question').value=question;}finally{busy=false;$('submit').disabled=false;$('reset').disabled=false;$('snapshot').disabled=false;$('progress').textContent='';$('question').focus();}};
$('question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('ask').requestSubmit();}};
$('reset').onclick=()=>{if(busy)return;history=[];$('messages').replaceChildren();$('question').value='';$('question').focus();};
api('/api/config').then(c=>{config=c;$('connection').textContent=`${c.engine} · ${c.cli} · 문서 ${c.documents}개`;}).catch(e=>{$('connection').textContent='연결 실패: '+e.message;$('submit').disabled=true;});
