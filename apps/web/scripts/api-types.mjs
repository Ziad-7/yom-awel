import fs from "node:fs/promises";
import openapiTS, { astToString } from "openapi-typescript";
const source = new URL("../../../contracts/openapi.json", import.meta.url);
const target = new URL("../src/lib/api/generated.ts", import.meta.url);
const output = astToString(await openapiTS(source));
if (process.argv.includes("--check")) {
  if (await fs.readFile(target, "utf8") !== output) throw new Error("API types drifted; run npm run api:generate");
} else await fs.writeFile(target, output);
