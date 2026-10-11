// Reads text out of screenshots in the browser with Tesseract. The images never
// leave the device: only the text the user then chooses to check is sent.
// The OCR engine and English data (~15 MB) are fetched from the jsDelivr CDN on
// first use and cached by the browser.

let workerPromise = null;
let onLog = () => {};

async function getWorker() {
  if (!workerPromise) {
    workerPromise = import("tesseract.js")
      .then(({ createWorker }) => createWorker("eng", 1, { logger: (m) => onLog(m) }))
      .catch((err) => {
        workerPromise = null; // allow a retry after a network failure
        throw err;
      });
  }
  return workerPromise;
}

/**
 * Read each file in turn. onProgress({ index, total, stage, percent }).
 * Returns one string per file (may be empty if no text was found).
 */
export async function readScreenshots(files, onProgress) {
  onProgress({ index: 0, total: files.length, stage: "loading", percent: null });
  onLog = (m) => {
    if (m.status === "loading language traineddata" || m.status === "loading tesseract core") {
      onProgress({ index: 0, total: files.length, stage: "loading", percent: Math.round((m.progress || 0) * 100) });
    }
  };
  const worker = await getWorker();
  const texts = [];
  try {
    for (let index = 0; index < files.length; index += 1) {
      onLog = (m) => {
        if (m.status === "recognizing text") {
          onProgress({ index, total: files.length, stage: "reading", percent: Math.round(m.progress * 100) });
        }
      };
      onProgress({ index, total: files.length, stage: "reading", percent: 0 });
      const { data } = await worker.recognize(files[index]);
      texts.push(cleanUp(data.text));
    }
  } finally {
    onLog = () => {};
  }
  return texts;
}

const TIMESTAMP = /^\d{1,2}[:.]\d{2}\s?(am|pm)?(\s?\S{0,3})?$/i;
const SENTENCE_END = /[.!?:)]$/;

/** Tidy OCR output: drop bare timestamps and rejoin lines that a chat bubble wrapped,
 *  so "earned 32%" / "per month" reads as one claim for the checker. */
export function cleanUp(text) {
  const lines = text.split("\n").map((line) => line.replace(/\s+/g, " ").trim());
  const out = [];
  for (const line of lines) {
    if (TIMESTAMP.test(line)) continue;
    const prev = out[out.length - 1];
    const continues = prev && line && !SENTENCE_END.test(prev) && /^[a-z0-9%$(]/.test(line);
    if (continues) out[out.length - 1] = `${prev} ${line}`;
    else if (line || (prev !== undefined && prev !== "")) out.push(line);
  }
  return out.join("\n").trim();
}
