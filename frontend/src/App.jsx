import { useEffect, useMemo, useState } from 'react';
import { HeartHandshake, LayoutDashboard, Package, Clock3, History, Plus, Truck, CheckCircle2, XCircle, RefreshCw, Leaf, MapPin, AlertTriangle } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const moneyDate = (s) => s?.replace('T',' ') || '';
async function request(path, options={}) {
  const res = await fetch(`${API}${path}`, {headers:{'Content-Type':'application/json'}, ...options});
  const data = await res.json().catch(()=>({detail:'Unexpected server response'}));
  if (!res.ok) {
    let msg = typeof data.detail === 'string' ? data.detail : data.detail?.reasons?.join('\n') || data.detail?.message || JSON.stringify(data.detail);
    throw new Error(msg || 'Request failed');
  }
  return data;
}
const initialDonation = {description:'',quantity_kg:10,pickup_from:'2026-03-10T18:00',pickup_until:'2026-03-10T20:00'};
export default function App(){
  const [data,setData] = useState(null);
  const [dashboard,setDashboard] = useState(null);
  const [actor,setActor] = useState('');
  const [tab,setTab] = useState('overview');
  const [notice,setNotice] = useState(null);
  const [busy,setBusy] = useState(false);
  const [donationForm,setDonationForm] = useState(initialDonation);
  const [claimForms,setClaimForms] = useState({});
  const [clockInput,setClockInput] = useState('');
  const [filter,setFilter] = useState('ALL');

  async function refresh(){
    const [d,stats] = await Promise.all([request('/api/bootstrap'),request('/api/dashboard')]);
    setData(d); setDashboard(stats); setClockInput(d.clock);
    if (!actor && d.donors.length) setActor(d.donors[0].id);
  }
  useEffect(()=>{refresh().catch(e=>setNotice({type:'error',text:e.message}));},[]);
  const person = useMemo(()=>data?.donors.find(x=>x.id===actor) || data?.volunteers.find(x=>x.id===actor),[data,actor]);
  const isDonor = Boolean(data?.donors.some(x=>x.id===actor));
  const myDonations = data?.donations.filter(d=>d.donor_id===actor) || [];
  const myClaims = data?.donations.flatMap(d=>(d.claims||[]).map(c=>({...c,donation:d}))).filter(c=>c.volunteer_id===actor) || [];
  const openDonations = data?.donations.filter(d=>d.status==='OPEN' && d.remaining_kg>0) || [];
  const visibleDonations = openDonations.filter(d=>filter==='ALL'||d.zone===filter);
  const activeClaimCount = myClaims.filter(c=>c.status==='ACTIVE').length;

  async function act(fn,success){
    setBusy(true); setNotice(null);
    try { await fn(); await refresh(); setNotice({type:'success',text:success}); }
    catch(e){setNotice({type:'error',text:e.message});}
    finally{setBusy(false);}
  }
  async function postDonation(e){
    e.preventDefault();
    await act(()=>request('/api/donations',{method:'POST',body:JSON.stringify({...donationForm,donor_id:actor,quantity_kg:Number(donationForm.quantity_kg)})}), 'Donation posted successfully.');
    setDonationForm(initialDonation);
  }
  async function makeClaim(d){
    const f=claimForms[d.id]||{kg:Math.min(5,d.remaining_kg),planned_time:d.pickup_from};
    await act(()=>request(`/api/donations/${d.id}/claims`,{method:'POST',body:JSON.stringify({volunteer_id:actor,kg:Number(f.kg),planned_time:f.planned_time})}), 'Food reserved successfully.');
  }
  async function changeClock(e){e.preventDefault();await act(()=>request('/api/clock',{method:'POST',body:JSON.stringify({clock:clockInput})}),'Simulated clock updated.');}
  if(!data) return <div className="loading"><div className="brand-mark"><HeartHandshake/></div><h2>Preparing food rescue…</h2><p>Connecting to SurplusLink</p></div>;
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><HeartHandshake size={24}/></div><div><strong>SurplusLink</strong><span>Food rescue network</span></div></div>
      <div className="side-label">WORKSPACE</div>
      <button className={`nav-item ${tab==='overview'?'active':''}`} onClick={()=>setTab('overview')}><LayoutDashboard size={18}/> Overview</button>
      <button className={`nav-item ${tab==='donations'?'active':''}`} onClick={()=>setTab('donations')}><Package size={18}/> Donations <span className="nav-count">{openDonations.length}</span></button>
      <button className={`nav-item ${tab==='claims'?'active':''}`} onClick={()=>setTab('claims')}><Truck size={18}/> My pickups</button>
      <button className={`nav-item ${tab==='history'?'active':''}`} onClick={()=>setTab('history')}><History size={18}/> Activity history</button>
      <div className="sidebar-bottom"><div className="live-dot"></div><div><b>Local demo mode</b><span>Persistent SQLite storage</span></div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div><div className="eyebrow">CITY FOOD RESCUE</div><h1>{tab==='overview'?'Community overview':tab==='donations'?'Food donations':tab==='claims'?'My pickups':'Activity history'}</h1></div><div className="actor-box"><span>Acting as</span><select value={actor} onChange={e=>{setActor(e.target.value);setNotice(null)}}><optgroup label="Restaurants / Donors">{data.donors.map(x=><option key={x.id} value={x.id}>{x.name} · {x.zone}</option>)}</optgroup><optgroup label="Volunteers">{data.volunteers.map(x=><option key={x.id} value={x.id}>{x.name} · {x.capacity_kg} kg</option>)}</optgroup></select></div></header>
      {notice&&<div className={`notice ${notice.type}`}><span>{notice.type==='success'?<CheckCircle2 size={18}/>:<AlertTriangle size={18}/>}</span><div>{notice.text.split('\n').map((x,i)=><div key={i}>{x}</div>)}</div><button onClick={()=>setNotice(null)}>×</button></div>}
      {tab==='overview'&&<Overview dashboard={dashboard} data={data} setTab={setTab} clockInput={clockInput} setClockInput={setClockInput} changeClock={changeClock} busy={busy}/>}
      {tab==='donations'&&<section className="content-grid">
        {isDonor?<div className="panel"><div className="panel-head"><div><div className="eyebrow">DONOR PORTAL</div><h2>Post surplus food</h2><p>Share safe, fresh food with nearby volunteers.</p></div><div className="icon-bubble"><Plus/></div></div>
          <form className="form" onSubmit={postDonation}><label>Food description<input required maxLength="160" value={donationForm.description} onChange={e=>setDonationForm({...donationForm,description:e.target.value})} placeholder="e.g. Fresh vegetable pulao"/></label><label>Quantity (kg)<input required type="number" min="1" step="1" value={donationForm.quantity_kg} onChange={e=>setDonationForm({...donationForm,quantity_kg:e.target.value})}/></label><div className="form-two"><label>Pickup starts<input type="datetime-local" required value={donationForm.pickup_from} onChange={e=>setDonationForm({...donationForm,pickup_from:e.target.value})}/></label><label>Pickup ends<input type="datetime-local" required value={donationForm.pickup_until} onChange={e=>setDonationForm({...donationForm,pickup_until:e.target.value})}/></label></div><button className="primary full" disabled={busy}><Plus size={17}/> Publish donation</button></form></div>
        :<div className="panel"><div className="panel-head"><div><div className="eyebrow">VOLUNTEER PORTAL</div><h2>Available food</h2><p>Reserve food in zones you can serve.</p></div><div className="icon-bubble"><Truck/></div></div><div className="filter-row"><span>Filter by zone</span><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="ALL">All permitted zones</option>{[...new Set(person?.zones||[])].map(z=><option key={z}>{z}</option>)}</select></div><div className="donation-list">{visibleDonations.filter(d=>(person?.zones||[]).includes(d.zone)).map(d=><DonationCard key={d.id} d={d} actor={actor} person={person} claimForm={claimForms[d.id]} setClaimForm={f=>setClaimForms({...claimForms,[d.id]:f})} onClaim={()=>makeClaim(d)} busy={busy}/>)}</div></div>}
        <div className="panel"><div className="panel-head"><div><div className="eyebrow">LIVE ROSTER</div><h2>{isDonor?'Your donations':'Open donations'}</h2><p>{isDonor?'Track claims and remaining quantities.':'Explore current food rescue opportunities.'}</p></div><button className="icon-button" onClick={()=>refresh()} title="Refresh"><RefreshCw size={17}/></button></div>
          <div className="donation-list">{(isDonor?myDonations:visibleDonations.filter(d=>(person?.zones||[]).includes(d.zone))).map(d=><DonationRow key={d.id} d={d} isDonor={isDonor} actor={actor} onCancel={()=>act(()=>request(`/api/donations/${d.id}/cancel`,{method:'POST',body:JSON.stringify({actor_id:actor})}),'Donation cancelled.')} busy={busy}/>)}</div>
        </div>
      </section>}
      {tab==='claims'&&<div className="panel"><div className="panel-head"><div><div className="eyebrow">VOLUNTEER PORTAL</div><h2>Your pickup reservations</h2><p>Collect or cancel active claims within the allowed time.</p></div><div className="icon-bubble"><Truck/></div></div>{!isDonor&&myClaims.length?myClaims.map(c=><div className="claim-row" key={c.id}><div className="food-avatar"><Package/></div><div className="claim-info"><b>{c.donation.description}</b><span>{c.kg} kg · {moneyDate(c.planned_time)} · {c.donation.zone}</span><small>{c.id} · {c.donation.id}</small></div><Status status={c.status}/><div className="row-actions">{c.status==='ACTIVE'&&<><button className="secondary small" disabled={busy} onClick={()=>act(()=>request(`/api/claims/${c.id}/collect`,{method:'POST',body:JSON.stringify({actor_id:actor})}),'Claim marked collected.')}>Collect</button><button className="ghost small" disabled={busy} onClick={()=>act(()=>request(`/api/claims/${c.id}/cancel`,{method:'POST',body:JSON.stringify({actor_id:actor})}),'Claim cancelled; quantity returned.')}>Cancel</button></>}</div></div>):<Empty text={isDonor?'Switch to a volunteer to see pickup reservations.':'No pickup reservations yet.'}/>}</div>}
      {tab==='history'&&<div className="panel"><div className="panel-head"><div><div className="eyebrow">AUDIT TRAIL</div><h2>Recent activity</h2><p>Every successful action is recorded with the simulated time.</p></div></div>{data.history.length?data.history.map(h=><div className="history-row" key={h.id}><div className="history-icon"><History size={16}/></div><div className="history-info"><b>{h.action.replaceAll('_',' ')}</b><span>{h.actor_name} · {h.donation_id||'System'} · {h.details}</span></div><time>{moneyDate(h.at)}</time></div>):<Empty text="Actions will appear here as the network is used."/>}</div>}
      <footer>SurplusLink <span>·</span> Rescue more. Waste less.</footer>
    </main>
  </div>
}
function Overview({dashboard:d,data,setTab,clockInput,setClockInput,changeClock,busy}){
  if(!d)return null;
  const metrics=[['Listed',d.listed_kg,'kg total','leaf'],['Collected',d.collected_kg,'kg rescued','check'],['Missed',d.missed_kg,'kg missed','clock'],['Wasted',d.wasted_kg,'kg expired','alert'],['In progress',d.in_progress_kg,'kg reserved','truck'],['Still open',d.still_open_kg,'kg available','package']];
  return <div className="overview"><div className="welcome"><div><div className="eyebrow light">SMALL ACTIONS. BIG IMPACT.</div><h2>Good food deserves<br/>a second chance.</h2><p>Connect surplus meals with volunteers who can get them where they're needed.</p><button className="light-button" onClick={()=>setTab('donations')}>Explore donations <span>→</span></button></div><div className="hero-art"><div className="sun"></div><div className="plate"><Leaf size={72}/></div><div className="floating-tag">♻ &nbsp; Food, not waste</div></div></div>
    <div className="section-title"><div><h2>Rescue dashboard</h2><p>Live totals across all non-cancelled donations</p></div><div className={`balance ${d.balanced?'good':'bad'}`}>{d.balanced?<CheckCircle2 size={16}/>:<AlertTriangle size={16}/>} {d.balanced?'Totals balanced':'Totals do not balance'}</div></div>
    <div className="metrics">{metrics.map((m,i)=><div className={`metric metric-${i}`} key={m[0]}><div className="metric-top"><span>{m[0]}</span><span className="metric-icon">{i===0?<Package/>:i===1?<CheckCircle2/>:i===2?<Clock3/>:i===3?<AlertTriangle/>:i===4?<Truck/>:<Leaf/>}</span></div><strong>{m[1]}<small>kg</small></strong><p>{m[2]}</p></div>)}</div>
    <div className="dashboard-lower"><div className="panel"><div className="panel-head"><div><h2>Food rescued by donor</h2><p>Collected kilograms by restaurant</p></div></div>{d.donor_stats.map(x=><StatBar key={x.id} name={x.name} value={x.collected_kg} max={Math.max(1,...d.donor_stats.map(y=>y.collected_kg))} unit="kg"/>)}</div><div className="panel"><div className="panel-head"><div><h2>Volunteer impact</h2><p>Rescue activity and missed pickups</p></div></div>{d.volunteer_stats.map(x=><div className="vol-stat" key={x.id}><div className="avatar">{x.name[0]}</div><div className="vol-stat-name"><b>{x.name}</b><span>{x.collected_kg} kg collected</span></div><span className={`missed-pill ${x.missed_claims?'warn':''}`}>{x.missed_claims} missed</span></div>)}</div></div>
    <div className="panel clock-panel"><div className="clock-symbol"><Clock3 size={22}/></div><div className="clock-copy"><h2>Simulated clock</h2><p>Move time forward to simulate pickup windows and expired food. The clock cannot go backwards.</p><strong>{moneyDate(data.clock)}</strong></div><form onSubmit={changeClock} className="clock-form"><label>Advance to<input type="datetime-local" value={clockInput} min={data.clock} onChange={e=>setClockInput(e.target.value)} required/></label><button className="primary" disabled={busy}>Update clock <span>→</span></button></form></div>
  </div>
}
function DonationCard({d,actor,person,claimForm,setClaimForm,onClaim,busy}){
 const f=claimForm||{kg:Math.min(5,d.remaining_kg),planned_time:d.pickup_from};
 const allowed=(person?.zones||[]).includes(d.zone);
 return <div className="donation-card"><div className="donation-card-top"><div className="food-avatar"><Package/></div><Status status={d.status}/></div><h3>{d.description}</h3><p className="donor-line">{d.donor_name} <span>·</span> <MapPin size={13}/> {d.zone}</p><div className="quantity-line"><strong>{d.remaining_kg} <small>kg</small></strong><span>of {d.quantity_kg} kg available</span></div><div className="progress"><span style={{width:`${Math.min(100,((d.quantity_kg-d.remaining_kg)/d.quantity_kg)*100)}%`}}/></div><div className="pickup-time"><Clock3 size={14}/>{moneyDate(d.pickup_from)} — {moneyDate(d.pickup_until)}</div><div className="claim-form"><label>Reserve kg<input type="number" min="1" step="1" max={d.remaining_kg} value={f.kg} onChange={e=>setClaimForm({...f,kg:e.target.value})}/></label><label>Planned pickup<input type="datetime-local" min={dataMin(d.pickup_from)} max={d.pickup_until} value={f.planned_time} onChange={e=>setClaimForm({...f,planned_time:e.target.value})}/></label><button className="primary full" disabled={busy||!allowed||d.remaining_kg<1} onClick={onClaim}>Reserve food <span>→</span></button>{!allowed&&<small className="inline-warning">Your zones do not include {d.zone}.</small>}</div></div>
}
function dataMin(s){return s||''}
function DonationRow({d,isDonor,actor,onCancel,busy}){
 return <div className="donation-row"><div className="food-avatar"><Package/></div><div className="donation-row-info"><b>{d.description}</b><span>{d.donor_name} · {d.zone} · {d.remaining_kg} kg remaining</span><small>{d.id} · {moneyDate(d.pickup_from)}–{moneyDate(d.pickup_until)}</small><div className="row-claims">{d.claims?.length?d.claims.map(c=><span key={c.id}>{c.volunteer_id}: {c.kg} kg · {c.status}</span>):<span>No claims yet</span>}</div></div><Status status={d.status}/>{isDonor&&d.status==='OPEN'&&<button className="ghost small" disabled={busy||d.claims?.some(c=>['ACTIVE','COLLECTED'].includes(c.status))} onClick={onCancel}>Cancel donation</button>}</div>
}
function StatBar({name,value,max,unit}){return <div className="stat-bar"><div><span>{name}</span><b>{value} {unit}</b></div><div className="bar-track"><span style={{width:`${value/max*100}%`}}/></div></div>}
function Status({status}){return <span className={`status status-${status?.toLowerCase()}`}>{status?.replace('_',' ')}</span>}
function Empty({text}){return <div className="empty"><Package size={28}/><p>{text}</p></div>}
