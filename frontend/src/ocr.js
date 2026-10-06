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

function cleanUp(text) {
  return text
    .split("\n")
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter((line, i, lines) => line || (i > 0 && lines[i - 1]))
    .join("\n")
    .trim();
}
