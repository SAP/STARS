// export function generateModelName(vendor: string, modelType: string, version: string, specialization: string, other: string, withVendor = true): string {
export function generateModelName(data: any[], vendor: string): any {
  const result: Record<string, string[]> = {};

  data.forEach(row => {
    const vendorName = vendor === '' ? row['vendor'] : vendor; // Si vendor est vide, on prend row['vendor'], sinon on utilise vendor existant

    const model = [row['modelType'], row['version'], row['specialization'], row['other']]
      .filter(value => value)
      .join('-')
      .replace(/\s+/g, ' ')
      .trim();

    if (!result[vendorName]) {
      result[vendorName] = [];
    }

    result[vendorName].push(model);
  });
  return result;
}

export function splitModelName(vendor: string, model: string): string[] {
  if (model.length < 18) return [vendor, model]; // No need to split

  // Find the last "-" before the 20th character
  const cutoffIndex = model.lastIndexOf('-', 20);

  if (cutoffIndex === -1) {
    // If no "-" found before 20, force split at 20
    return [vendor, model.slice(0, 20), model.slice(20)];
  }

  // Split at the last "-" before 20
  return [vendor, model.slice(0, cutoffIndex), model.slice(cutoffIndex + 1)].map(capitalizeFirstLetter);
}

export function capitalizeFirstLetter(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
