export async function getFlaps() {
  let flapsRequest = await fetch("/api/v1/display/flap");
  return await flapsRequest.json();
}