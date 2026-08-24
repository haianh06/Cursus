/**
 * Keeps async UI regions honest when an identifier or filter changes before a
 * request finishes. Consumers start a generation before fetching and commit
 * only if it is still current when the promise resolves.
 */
export function createRequestGeneration() {
  let activeGeneration = 0;

  return {
    begin() {
      activeGeneration += 1;
      return activeGeneration;
    },
    isCurrent(generation) {
      return generation === activeGeneration;
    },
  };
}
