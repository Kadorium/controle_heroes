import { expect, it } from "vitest";
import { fitRecordActions } from "./recordActionLayout";

it("uses rendered widths, trigger and gaps, with no numerical ceiling", () => {
  expect(fitRecordActions([80,80,80,80,80], 450, 110, true)).toBe(5);
  expect(fitRecordActions([180,80,80,80,80], 450, 110, true)).toBe(2);
  expect(fitRecordActions([180,80,80,80,80], 230, 110, true)).toBe(1);
  expect(fitRecordActions([], 0, 110, false)).toBe(0);
});
it("is monotone across slow resizing and always chooses the maximal ordered prefix", () => {
  const widths=[134.4,98.8,163.6,94.2,200.8], trigger=116.5;
  let previous=0;
  for(let width=275;width<850;width+=0.25){
    const count=fitRecordActions(widths,width,trigger,true);
    expect(count).toBeGreaterThanOrEqual(previous);
    if(count>1 && count<widths.length) expect(widths.slice(0,count).reduce((a,b)=>a+b,0)+8*count+trigger).toBeLessThanOrEqual(width-2);
    previous=count;
  }
});
