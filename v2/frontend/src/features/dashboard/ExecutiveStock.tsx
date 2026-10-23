import type { User } from "../auth/types";
import { StockExplorer } from "../inventory/StockExplorer";
export function ExecutiveStock({refreshKey,user}:{refreshKey:number;user:User}) {return <StockExplorer user={user} compact refreshKey={refreshKey}/>;}
