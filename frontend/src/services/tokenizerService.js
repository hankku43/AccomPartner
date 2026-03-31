// src/services/tokenizerService.js

class MidiTokenizer {
    constructor() {
        this.vocab = null;
        this.idToToken = {};
        this.durationKeys = [];
        this.velocityKeys = [];
        this.isReady = false;
    }

    // 1. 載入並解析 tokenizer.json
    async init() {
        if (this.isReady) return;
        try {
            const response = await fetch('/vocab.json');
            const data = await response.json();
            this.vocab = data.model ? data.model.vocab : data.vocab; // 兼容不同版本的 miditok 格式

            // 建立反向查詢字典
            for (const [key, id] of Object.entries(this.vocab)) {
                this.idToToken[id] = key;
                if (key.startsWith('Duration_')) this.durationKeys.push(key);
                if (key.startsWith('Velocity_')) this.velocityKeys.push(key);
            }
            this.isReady = true;
            console.log("✅ Tokenizer 字典載入完成！詞彙量:", Object.keys(this.vocab).length);
        } catch (error) {
            console.error("❌ Tokenizer 載入失敗:", error);
        }
    }



    // 2. 將使用者的彈奏 (秒) 與 上一小節伴奏 轉換為模型輸入 (Token IDs)
    encodeBar(melodyNotes, accompNotes, bpm) {
        if (!this.isReady) throw new Error("Tokenizer 尚未載入");

        const ticksPerBeat = 4; // 解析度: 一拍 4 個 16 分音符
        const secPerBeat = 60 / bpm;
        const secPerTick = secPerBeat / ticksPerBeat;

        // 起手式: BOS 與 Bar_None
        let tokens = ['BOS_None', 'Bar_None'];
        const events = [];

        // 🌟 1. 完整還原：將秒數轉換為精準的 Duration Token
        const getDurationToken = (durationSec) => {
            let totalTicks = Math.round(durationSec / secPerTick);
            if (totalTicks < 1) totalTicks = 1; // 至少 1 個 tick (Duration_0.1.4)
            if (totalTicks > 32) totalTicks = 32; // 最高限制 8 拍 (Duration_8.0.4)

            const beats = Math.floor(totalTicks / 4);
            const ticks = totalTicks % 4;
            const durStr = `Duration_${beats}.${ticks}.4`;

            // 如果算出來的長度在字典裡，就用它，否則給個預設值保底
            return this.durationKeys.includes(durStr) ? durStr : 'Duration_1.0.4';
        };

        // 🌟 2. 智慧量化函數 (網格對齊)
        const quantizeTime = (time) => {
            const rawPos = time / secPerTick;
            let snappedPos = Math.round(rawPos);
            // 限制在 0~15 的合法範圍內
            snappedPos = Math.max(0, Math.min(snappedPos, 15));
            return snappedPos;
        };

        // 🌟 3. 和弦對齊邏輯 (Chord Grouping)
        let allInputNotes = [];
        melodyNotes.forEach(n => allInputNotes.push({ ...n, program: 0 }));
        accompNotes.forEach(n => allInputNotes.push({ ...n, program: 1 }));

        // 依照真實的物理彈奏時間排序
        allInputNotes.sort((a, b) => a.time - b.time);

        // 如果兩個音符彈奏的時間差小於 50 毫秒，就視為同時按下的和弦
        const CHORD_TOLERANCE_SEC = 0.05;

        let currentChordPos = -1;
        let currentChordTime = -1;

        allInputNotes.forEach(n => {
            let finalPos;

            // 檢查是否與前一個音符極度接近 (防呆：人類彈奏誤差)
            if (currentChordTime !== -1 && Math.abs(n.time - currentChordTime) < CHORD_TOLERANCE_SEC) {
                finalPos = currentChordPos; // 強制吸附到前一個音的 Position
            } else {
                finalPos = quantizeTime(n.time); // 重新計算網格
                currentChordTime = n.time;       // 更新基準時間
                currentChordPos = finalPos;      // 更新基準網格
            }

            events.push({
                pos: finalPos,
                program: n.program,
                pitch: n.midi,
                velocity: 79, // 固定力度
                durationStr: getDurationToken(n.duration)
            });
        });

        // 🌟 4. 嚴格依照 Position -> Program -> Pitch 排序 (符合模型訓練的嚴格格式)
        events.sort((a, b) => {
            if (a.pos !== b.pos) return a.pos - b.pos;
            if (a.program !== b.program) return a.program - b.program;
            return a.pitch - b.pitch;
        });

        // 🌟 5. 將事件陣列攤平成一維 Token 序列
        let currentPos = -1;
        for (const ev of events) {
            if (ev.pos !== currentPos) {
                tokens.push(`Position_${ev.pos}`);
                currentPos = ev.pos;
            }
            tokens.push(`Program_${ev.program}`);
            tokens.push(`Pitch_${ev.pitch}`);
            tokens.push(`Velocity_${ev.velocity}`);
            tokens.push(ev.durationStr);
        }

        tokens.push('EOS_None');

        // 將字串轉為模型看得懂的整數 ID
        return tokens.map(t => this.vocab[t] !== undefined ? this.vocab[t] : this.vocab['PAD_None']);
    }

    // 3. 將模型生成的伴奏 (Token IDs) 轉換為 Tone.js 音符 (秒)
    decodeAccompaniment(tokenIds, bpm) {
        if (!this.isReady) return [];

        const ticksPerBeat = 4;
        const secPerBeat = 60 / bpm;
        const secPerTick = secPerBeat / ticksPerBeat;

        let notes = [];
        let currentPos = 0;
        let currentNote = {};

        for (const id of tokenIds) {
            const tokenStr = this.idToToken[id];
            if (!tokenStr) continue;

            const [type, value] = tokenStr.split('_');

            if (type === "Position") {
                currentPos = parseInt(value);
            } else if (type === "Pitch") {
                currentNote.midi = parseInt(value);
            } else if (type === "Duration") {
                // 解析 miditok 的時長格式 (假設是 Beat.Tick.Subtick)
                const parts = value.split('.');
                let totalTicks = 4; // 預設 1 拍
                if (parts.length >= 2) {
                    const beats = parseInt(parts[0]);
                    const ticks = parseInt(parts[1]);
                    totalTicks = (beats * ticksPerBeat) + ticks;
                }

                notes.push({
                    midi: currentNote.midi,
                    time: currentPos * secPerTick,
                    duration: totalTicks * secPerTick
                });
                currentNote = {}; // 重置
            }
        }
        return notes;
    }
}

export const tokenizerService = new MidiTokenizer();