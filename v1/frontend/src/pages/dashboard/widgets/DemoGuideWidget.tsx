import { Link } from "react-router-dom";
import { Button } from "../../../components";
import { DEMO_SCENARIOS } from "../../../constants/demoScenarios";

export function DemoGuideWidget() {
  return (
    <div className="demo-guide-banner card">
      <div>
        <h3>Demo Epic</h3>
        <p className="meta">
          {DEMO_SCENARIOS.length} cenários operacionais prontos para apresentar à equipe.
        </p>
      </div>
      <Link to="/demo">
        <Button variant="secondary">Abrir roteiro</Button>
      </Link>
    </div>
  );
}
