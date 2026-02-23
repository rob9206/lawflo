export function parseContent(raw: string): string {
  if (!raw) {
    return "";
  }

  let cleaned = raw;
  const jsonTailPatterns = [
    /,?\s*"?_covered"?\s*:\s*\[.*$/s,
    /,?\s*"?weakness_detected"?\s*:.*$/s,
    /,?\s*\d+\.\d+\s*,?\s*"?:?\s*\{.*$/s,
    /,?\s*"?next_topic"?\s*:.*$/s,
  ];

  for (const pattern of jsonTailPatterns) {
    cleaned = cleaned.replace(pattern, "");
  }

  cleaned = cleaned.replace(/^#{1,6}\s*/gm, "");
  cleaned = cleaned.replace(/\*\*([^*]*)\*\*/g, "$1");
  cleaned = cleaned.replace(/\*{1,2}(?!\*)/g, "");
  cleaned = cleaned.replace(/\n[ \t]+/g, "\n");
  cleaned = cleaned.replace(/[ \t]+/g, " ");
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

  return cleaned.trim();
}
