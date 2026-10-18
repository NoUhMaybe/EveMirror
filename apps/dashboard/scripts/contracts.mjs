import { readFile, writeFile, mkdir } from "node:fs/promises";
import { compile } from "json-schema-to-typescript";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import standaloneCode from "ajv/dist/standalone/index.js";
import { build } from "esbuild";
import { format } from "prettier";
import { fileURLToPath } from "node:url";

const schema = JSON.parse(
  await readFile(
    new URL(
      "../../../packages/application/browser.schema.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const output = await format(
  await compile(schema, "BrowserFrame", {
    bannerComment:
      "/* Generated from packages/application/browser.schema.json. Run npm run contracts. */",
    additionalProperties: false,
  }),
  { parser: "typescript" },
);
const destination = new URL("../src/types/contracts.d.ts", import.meta.url);
await mkdir(new URL("../src/types/", import.meta.url), { recursive: true });
if (process.argv.includes("--check")) {
  if ((await readFile(destination, "utf8")) !== output)
    throw Error("Browser TypeScript contract drift");
} else await writeFile(destination, output);

const ajv = new Ajv({ strict: false, code: { source: true } });
addFormats(ajv);
const validate = ajv.compile(schema);
const bundled = await build({
  absWorkingDir: fileURLToPath(new URL("../", import.meta.url)),
  tsconfigRaw: {},
  nodePaths: [fileURLToPath(new URL("../node_modules/", import.meta.url))],
  stdin: {
    contents: standaloneCode(ajv, validate),
    resolveDir: fileURLToPath(new URL("..", import.meta.url)),
    sourcefile: "browser-validator.cjs",
    loader: "js",
  },
  bundle: true,
  format: "esm",
  platform: "browser",
  write: false,
  legalComments: "none",
});
const validator = await format(
  "/* Generated at build time; CSP-safe, no runtime schema compiler. */\n" +
    bundled.outputFiles[0].text,
  { parser: "babel" },
);
const validatorPath = new URL("../src/types/validate.mjs", import.meta.url);
if (process.argv.includes("--check")) {
  if ((await readFile(validatorPath, "utf8")) !== validator)
    throw Error("Browser validator drift");
} else await writeFile(validatorPath, validator);
