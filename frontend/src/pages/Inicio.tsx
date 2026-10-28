import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, cop, parsePage, type Actividad, type Recaudo, type Totales } from "../api";
import { Pager, slicePage } from "../components/Pager";
import { useAuth } from "../auth";

export function Inicio() {
  const { organizacion } = useAuth();
  const [totales, setTotales] = useState<Totales | null>(null);
  const [recientes, setRecientes] = useState<Recaudo[]>([]);
  const [actividades, setActividades] = useState<Actividad[]>([]);
  const [pageAct, setPageAct] = useState(1);
  const [pagesAct, setPagesAct] = useState(1);
  const [countAct, setCountAct] = useState(0);
  const [pagePago, setPagePago] = useState(1);
  const [pagesPago, setPagesPago] = useState(1);
  const [countPago, setCountPago] = useState(0);
  const [pagePad, setPagePad] = useState(1);

  const loadActividades = async (pagina = 1) => {
    const data = parsePage<Actividad>(await api(`/api/actividades/?page=${pagina}`));
    setActividades(data.results);
    setPagesAct(data.pages);
    setCountAct(data.count);
    setPageAct(data.page);
  };

  const loadPagos = async (pagina = 1) => {
    const recaudos = await api<{ resultados: Recaudo[]; totales: Totales }>(`/api/recaudos/?page=${pagina}`);
    const page = parsePage<Recaudo>(recaudos);
    setTotales(recaudos.totales);
    setRecientes(page.results);
    setPagesPago(page.pages);
    setCountPago(page.count);
    setPagePago(page.page);
  };

  useEffect(() => {
    void loadPagos(1);
    void loadActividades(1);
  }, []);

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="eyebrow">Flujo diario</div>
          <h1>{organizacion?.nombre || "Recaudo"}</h1>
          <p className="muted">
            La familia paga al padrino. Usted digita el valor; si es transferencia adjunta el comprobante. Eso entra en
            la sumatoria de la actividad.
          </p>
        </div>
        <Link className="btn gold" to="/recaudos/nuevo">
          Registrar pago
        </Link>
      </div>
      <div className="grid">
        <div className="card">
          <div className="muted">Total recaudado</div>
          <div className="kpi">{totales?.total_confirmado_formato || "$0"}</div>
        </div>
        <div className="card">
          <div className="muted">Pagos registrados</div>
          <div className="kpi">{totales?.cantidad_confirmados ?? 0}</div>
        </div>
      </div>

      <h2 style={{ margin: "24px 0 12px" }}>Sumatoria por actividad</h2>
      <div className="list">
        {actividades.length === 0 ? (
          <p className="muted">
            Primero cree un padrino, una actividad y las familias.{" "}
            <Link to="/actividades/nueva">Nueva actividad</Link>
          </p>
        ) : null}
        {actividades.map((actividad) => (
          <Link className="list-item" key={actividad.id} to={`/actividades/${actividad.id}`}>
            <div>
              <strong>{actividad.nombre}</strong>
              <div className="muted">{actividad.cantidad_recaudos || 0} pagos de familias</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="kpi" style={{ fontSize: "1.1rem" }}>
                {cop(actividad.total_recaudado)}
              </div>
              <span className={`badge ${actividad.estado}`}>{actividad.estado}</span>
            </div>
          </Link>
        ))}
      </div>
      <Pager page={pageAct} pages={pagesAct} count={countAct} label="actividades" onChange={(p) => void loadActividades(p)} />

      <h2 style={{ margin: "24px 0 12px" }}>Sumatoria por padrino</h2>
      <div className="list">
        {slicePage(totales?.por_padrino || [], pagePad).pageItems.map((row) => (
          <Link className="list-item" key={row.id || row.nombre} to={row.id ? `/padrinos/${row.id}` : "/padrinos"}>
            <div>
              <strong>{row.nombre}</strong>
              <div className="muted">{row.cantidad} pagos</div>
            </div>
            <div>{row.total_formato || cop(row.total)}</div>
          </Link>
        ))}
        {!totales?.por_padrino?.length ? <p className="muted">Cuando registre el primer pago, verá el total de cada padrino.</p> : null}
      </div>
      <Pager
        page={pagePad}
        pages={slicePage(totales?.por_padrino || [], pagePad).pages}
        count={totales?.por_padrino.length || 0}
        label="padrinos"
        onChange={setPagePad}
      />

      <div className="toolbar" style={{ marginTop: 24 }}>
        <h2 style={{ margin: 0 }}>Pagos</h2>
        <Link className="btn secondary" to="/pagos">
          Ver y administrar
        </Link>
      </div>
      <div className="list">
        {recientes.map((item) => (
          <Link className="list-item" key={item.id} to={`/recaudos/${item.id}`}>
            <div>
              <strong>{item.aportante_nombre}</strong>
              <div className="muted">
                Recibo {item.numero_formateado} · {item.actividad_nombre}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div>{item.valor_formato}</div>
              <span className={`badge ${item.estado}`}>{item.estado_display}</span>
            </div>
          </Link>
        ))}
      </div>
      <Pager page={pagePago} pages={pagesPago} count={countPago} label="pagos" onChange={(p) => void loadPagos(p)} />
    </div>
  );
}
