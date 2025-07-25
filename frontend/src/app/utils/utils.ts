// Function to split model names longer than 18 characters into two parts to fit in the ui y-axis
export function splitModelName(model: string): string[] {
  if (model.length < 18) return [capitalizeFirstLetter(model)]; // No need to split

  // Find the last "-" before the 20th character
  const cutoffIndex = model.lastIndexOf('-', 20);

  if (cutoffIndex === -1) {
    // If no "-" found before 20, force split at 20
    return [model.slice(0, 20), model.slice(20)];
  }

  // Split at the last "-" before 20
  return [capitalizeFirstLetter(model.slice(0, cutoffIndex)), model.slice(cutoffIndex + 1)];
}

export function capitalizeFirstLetter(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
