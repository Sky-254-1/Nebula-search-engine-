import { SpeechRecognition } from '@capacitor-community/speech-recognition';

export async function startVoiceSearch(): Promise<string | null> {
  const available = await SpeechRecognition.available();
  if (!available.available) return null;
  await SpeechRecognition.requestPermissions();
  const result = await SpeechRecognition.start({ language: 'en-US', maxResults: 1 });
  return result.matches?.[0] ?? null;
}

export async function stopVoiceSearch() {
  await SpeechRecognition.stop();
}
