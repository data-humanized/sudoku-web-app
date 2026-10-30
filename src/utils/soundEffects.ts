/**
 * Procedural Web Audio synthesizer for minimalist Zen audio feedback.
 * 100% offline, zero external asset dependencies.
 *
 * Rules:
 * - Shared constant: SOUND_GAIN = { correct: 0.25, wrong: 0.25, erase: 0.12 }
 * - Correct digit: Short, soft, clean tick/pop (80-120 ms). Gain = 0.25.
 * - Wrong-digit: Existing Erase sound (descending 320 Hz -> 80 Hz sine ramp). Gain = 0.25.
 * - Erase action: Realistic pencil scribble on paper with softer volume (gain = 0.12).
 * - Old wrong-input sound (sawtooth) deleted completely.
 * - All other actions (placement, notes, undo/redo, hints, navigation) are silent.
 * - Respects the sound on/off user setting.
 */

export const SOUND_GAIN = {
  correct: 0.25,
  wrong: 0.25,
  erase: 0.12,
} as const;

class SoundManager {
  private ctx: AudioContext | null = null;
  public enabled: boolean = true;

  private initCtx() {
    if (!this.ctx && typeof window !== 'undefined') {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
  }

  /**
   * Correct digit action:
   * Short, soft, clean tick or pop, about 80-120 ms.
   * Uses SOUND_GAIN.correct (0.25) so it is clearly audible.
   */
  playCorrect() {
    if (!this.enabled) return;
    try {
      this.initCtx();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const now = this.ctx.currentTime;

      osc.type = 'sine';
      // Soft clean pop/tick (starts at 560 Hz, quickly drops to 240 Hz over 90ms)
      osc.frequency.setValueAtTime(560, now);
      osc.frequency.exponentialRampToValueAtTime(240, now + 0.09);

      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.linearRampToValueAtTime(SOUND_GAIN.correct, now + 0.008);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.09);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.095);
    } catch {}
  }

  /**
   * Wrong-digit action:
   * Reuses the EXISTING Erase button sound (sine 320 Hz -> 80 Hz exponential ramp).
   * Uses SOUND_GAIN.wrong (0.25).
   */
  playWrongDigit() {
    if (!this.enabled) return;
    try {
      this.initCtx();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const now = this.ctx.currentTime;

      osc.type = 'sine';
      osc.frequency.setValueAtTime(320, now);
      osc.frequency.exponentialRampToValueAtTime(80, now + 0.14);

      gain.gain.setValueAtTime(SOUND_GAIN.wrong, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.15);
    } catch {}
  }

  /**
   * Erase button:
   * Realistic pencil scribbling on rough paper.
   * Scaled with SOUND_GAIN.erase (0.12) so it is comfortably soft to the ear.
   */
  playErase() {
    if (!this.enabled) return;
    try {
      this.initCtx();
      if (!this.ctx) return;

      const duration = 0.30; // 300 ms (within 250-400 ms range)
      const sampleRate = this.ctx.sampleRate;
      const bufferSize = Math.floor(sampleRate * duration);
      const buffer = this.ctx.createBuffer(1, bufferSize, sampleRate);
      const data = buffer.getChannelData(0);

      // White/textured friction noise
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * 0.75;
      }

      const noiseSource = this.ctx.createBufferSource();
      noiseSource.buffer = buffer;

      // Band-pass filter centered on pencil-paper friction resonance (~2200 Hz)
      const bandpass = this.ctx.createBiquadFilter();
      bandpass.type = 'bandpass';
      bandpass.frequency.setValueAtTime(2200, this.ctx.currentTime);
      bandpass.Q.setValueAtTime(2.2, this.ctx.currentTime);

      // High-pass filter to clean up low rumble
      const highpass = this.ctx.createBiquadFilter();
      highpass.type = 'highpass';
      highpass.frequency.setValueAtTime(1100, this.ctx.currentTime);

      const gain = this.ctx.createGain();
      const now = this.ctx.currentTime;
      gain.gain.setValueAtTime(0.0001, now);

      // Jittery amplitude envelope simulating 3 rapid pencil scratch strokes
      // Scaled to SOUND_GAIN.erase (0.12)
      gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.85, now + 0.025);
      gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.20, now + 0.075);
      gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase, now + 0.115);
      gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.25, now + 0.175);
      gain.gain.linearRampToValueAtTime(SOUND_GAIN.erase * 0.75, now + 0.22);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      noiseSource.connect(bandpass);
      bandpass.connect(highpass);
      highpass.connect(gain);
      gain.connect(this.ctx.destination);

      noiseSource.start(now);
      noiseSource.stop(now + duration);
    } catch {}
  }

  // Alias for backward-compatibility if invoked on correct digit
  playClick() {
    this.playCorrect();
  }

  // Silent no-ops for all other actions (undo/redo, hints, pencil notes, navigation)
  playNote() {}
  playVictory() {}
}

export const sounds = new SoundManager();
