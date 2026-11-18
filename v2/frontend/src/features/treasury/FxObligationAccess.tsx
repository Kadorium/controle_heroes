import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../ui";

/** An FX permission does not authorize listing the accounts payable queue. */
export function FxObligationAccess() {
  const [id,setId]=useState("");
  const navigate=useNavigate();
  const valid=/^[1-9]\d*$/.test(id) && Number.isSafeInteger(Number(id));
  return <section className="panel dense">
    <PageHeader title="Câmbio por obrigação" />
    <form onSubmit={event=>{event.preventDefault();if(valid)navigate(`/payables/${id}/fx`);}}>
      <label htmlFor="fx-obligation-id">Número da obrigação</label>
      <div className="stack-row">
        <input id="fx-obligation-id" inputMode="numeric" value={id} onChange={event=>setId(event.target.value.trim())} />
        <button type="submit" className="ui-button" disabled={!valid}>Abrir câmbio</button>
      </div>
    </form>
  </section>;
}
