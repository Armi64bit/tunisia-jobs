export function fmtKB(n: number): string {
  return `${Math.round(n / 1024)} KB`;
}

export function timeNow(): string {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

let lineSeq = 0;
export function nextLogId(): number {
  lineSeq += 1;
  return lineSeq;
}