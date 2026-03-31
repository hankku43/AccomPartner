// src/services/aiService.js
import { env, AutoModelForSeq2SeqLM, Tensor } from '@huggingface/transformers';

// ==========================================
// 1. 環境設定
// ==========================================
env.allowRemoteModels = false; 
env.allowLocalModels = true;

class AccompanimentAI {
    constructor() {
        this.model = null;
        this.isReady = false;
        this.isLoading = false;
    }

    /**
     * 初始化並載入模型 (在網頁剛打開時呼叫)
     */
    async init() {
        if (this.isReady || this.isLoading) return;
        
        try {
            this.isLoading = true;
            console.log("⏳ 準備載入 AI 伴奏模型...");
            
            // '/frontend_model' 對應到你 public 資料夾下的路徑
            this.model = await AutoModelForSeq2SeqLM.from_pretrained('/frontend_model', {
                quantized: true, // 啟用前端量化，能將記憶體佔用砍半，提升推論速度
            });

            this.isReady = true;
            console.log("✅ ONNX 伴奏模型載入完成！");
        } catch (error) {
            console.error("❌ 模型載入失敗:", error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * 預測下一小節的伴奏
     * @param {Array<number>} currentBarTokenIds - 前端轉換好的整數陣列
     * @returns {Promise<Array<number>>} - 生成的下一小節 Token 陣列
     */
    async generateNextBar(currentBarTokenIds) {
        if (!this.isReady) {
            console.warn("⚠️ 模型尚未載入完成，請稍候。");
            return [];
        }

        console.log("🧠 AI 思考中... 輸入長度:", currentBarTokenIds.length);
        const startTime = performance.now();

        try {
            const seqLen = currentBarTokenIds.length;

            // 1. 建立 input_ids 張量 (轉為 64位元整數)
            const inputIds = new Tensor(
                'int64', 
                new BigInt64Array(currentBarTokenIds.map(id => BigInt(id))), 
                [1, seqLen]
            );

            // 🌟 2. 建立 attention_mask 張量 (全部填 1，告訴模型每一個 Token 都要注意)
            const maskData = new BigInt64Array(seqLen);
            maskData.fill(1n);
            const attentionMask = new Tensor('int64', maskData, [1, seqLen]);

            // 3 & 4. 將「輸入張量」與「推論參數」合併成單一個大 Object 傳入
            const generationKwargs = {
                input_ids: inputIds,
                attention_mask: attentionMask,
                max_new_tokens: 512,     // 🌟 這次絕對不會被忽略了
                temperature: 1.0,       
                top_k: 50,              
                top_p: 0.9,             
                do_sample: true,
                repetition_penalty: 1.2, // 降低重複按同一個音的機率
                pad_token_id: 0,        
                bos_token_id: 1,        
                eos_token_id: 2,       
            };

            // 呼叫底層的 ONNX Runtime 進行推論 (只傳入單一參數)
            const output = await this.model.generate(generationKwargs);

            // 🌟 5. 把算出來的 Tensor 解碼回 JavaScript 的普通 Number 陣列
            // output.data 是一個 BigInt64Array，我們將其轉回一般數字
            let generatedTokens = Array.from(output.data).map(n => Number(n));
            
            // 🌟 6. 完美還原你 Python 腳本裡的邏輯：切除開頭的 BOS (1) 與結尾的 EOS (2)
            if (generatedTokens[0] === 1) { 
                generatedTokens.shift();
            }
            const eosIndex = generatedTokens.indexOf(2); 
            if (eosIndex !== -1) {
                generatedTokens = generatedTokens.slice(0, eosIndex);
            }

            const endTime = performance.now();
            console.log(`✨ 推論完成！耗時: ${(endTime - startTime).toFixed(2)} 毫秒`);

            return generatedTokens;

        } catch (error) {
            console.error("❌ 推論過程中發生錯誤:", error);
            return [];
        }
    }
}

// 導出一個單一實例 (Singleton)，確保全站共用同一個模型記憶體
export const aiService = new AccompanimentAI();