/** Resolve the runtime's extensionless imports when running under Node.
 *
 * The app is bundled by Vite, which resolves `./board` to `./board.ts`
 * itself. Node's ESM resolver requires the extension, so this hook adds it —
 * nothing else. The module bytes Node executes are the same ones the browser
 * gets, which is the whole point of running parity against these files rather
 * than against a copy.
 */

import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, resolve as resolvePath } from "node:path";

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith(".") && !/\.[a-z]+$/i.test(specifier)) {
    const base = dirname(fileURLToPath(context.parentURL));
    const candidate = resolvePath(base, `${specifier}.ts`);
    if (existsSync(candidate)) {
      return { url: pathToFileURL(candidate).href, shortCircuit: true };
    }
  }
  return nextResolve(specifier, context);
}
