/** Exactly two immutable, tenant-bound copies. No fetch, storage or silent swap. */
import { compareBytes, compareObject, compareRequire, copyComparableDevice, copyCompareContext,
  freezeComparison, MAX_COMPARE_BYTES } from "./compareModel";
import type { ComparableDevice, CompareContext, CompareSide, CompareSlots, CompareState } from "./compareModel";

function finish(contextValue: CompareContext, slotsValue: CompareSlots): CompareState {
  const context = copyCompareContext(contextValue);
  compareRequire(Array.isArray(slotsValue) && slotsValue.length === 2);
  const left = slotsValue[0] === null ? null : copyComparableDevice(slotsValue[0]);
  const right = slotsValue[1] === null ? null : copyComparableDevice(slotsValue[1]);
  compareRequire((left === null || left.tenantId === context.tenantId) && (right === null || right.tenantId === context.tenantId), "context_mismatch");
  compareRequire(left === null || right === null || left.deviceId !== right.deviceId, "duplicate_device");
  const slots: CompareSlots = [left, right];
  const result = { context, slots, bytes: 0 };
  // Include the bytes field in the actual complete UTF-8 selection budget.
  for (let i = 0; i < 4; i++) {
    const measured = compareBytes(result); if (measured === result.bytes) break; result.bytes = measured;
  }
  compareRequire(result.bytes === compareBytes(result) && result.bytes <= MAX_COMPARE_BYTES, "size_limit");
  return freezeComparison(result);
}
export function copyCompareState(input: CompareState): CompareState {
  compareObject(input, ["context", "slots", "bytes"]);
  compareRequire(Number.isSafeInteger(input.bytes) && input.bytes >= 0 && input.bytes <= MAX_COMPARE_BYTES, "size_limit");
  const result = finish(input.context, input.slots); compareRequire(result.bytes === input.bytes);
  return result;
}
export function createCompareState(context: CompareContext): CompareState { return finish(context, [null, null]); }
function checkedDevice(state: CompareState, input: ComparableDevice): ComparableDevice {
  const device = copyComparableDevice(input);
  compareRequire(device.tenantId === state.context.tenantId, "context_mismatch");
  return device;
}
export function addComparableDevice(input: CompareState, value: ComparableDevice): CompareState {
  const state = copyCompareState(input), device = checkedDevice(state, value);
  compareRequire(!state.slots.some((item) => item?.deviceId === device.deviceId), "duplicate_device");
  if (state.slots[0] === null) return finish(state.context, [device, state.slots[1]]);
  compareRequire(state.slots[1] === null, "selection_full");
  return finish(state.context, [state.slots[0], device]);
}
export function updateComparableDevice(input: CompareState, value: ComparableDevice): CompareState {
  const state = copyCompareState(input), device = checkedDevice(state, value);
  compareRequire(state.slots.some((item) => item?.deviceId === device.deviceId), "device_not_found");
  return finish(state.context, [state.slots[0]?.deviceId === device.deviceId ? device : state.slots[0],
    state.slots[1]?.deviceId === device.deviceId ? device : state.slots[1]]);
}
export function replaceSlot(input: CompareState, side: CompareSide, value: ComparableDevice): CompareState {
  compareRequire(side === "left" || side === "right", "invalid_slot");
  const state = copyCompareState(input), device = checkedDevice(state, value);
  // Existing selected devices use the separate explicit update action.
  compareRequire(!state.slots.some((item) => item?.deviceId === device.deviceId), "duplicate_device");
  return side === "left" ? finish(state.context, [device, state.slots[1]]) : finish(state.context, [state.slots[0], device]);
}
export function removeComparableDevice(input: CompareState, deviceId: string): CompareState {
  const state = copyCompareState(input);
  compareRequire(typeof deviceId === "string" && state.slots.some((item) => item?.deviceId === deviceId), "device_not_found");
  // Keep the other side in place; removing left never silently moves right.
  return finish(state.context, [state.slots[0]?.deviceId === deviceId ? null : state.slots[0],
    state.slots[1]?.deviceId === deviceId ? null : state.slots[1]]);
}
export function clearCompareState(input: CompareState): CompareState {
  const state = copyCompareState(input); return finish(state.context, [null, null]);
}
