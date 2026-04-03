import os
import time
import logging
import tempfile
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

# 暫存檔保留時間 (1 小時)
CLEANUP_THRESHOLD_SECONDS = 3600
# 掃描間隔時間 (30 分鐘)
CLEANUP_INTERVAL_SECONDS = 1800
# 暫存檔前綴 (確保只刪除本專案產生的檔案)
TEMP_FILE_PREFIX = "accom_tmp_"

def cleanup_old_temp_files():
    """
    掃描系統暫存目錄，刪除超過 1 小時且帶有特定前綴的 MIDI 暫存檔。
    """
    temp_dir = Path(tempfile.gettempdir())
    logger.info(f"🧹 開始掃描暫存目錄: {temp_dir}")
    
    count = 0
    now = time.time()
    
    try:
        # 遍歷暫存目錄下的所有檔案
        for file_path in temp_dir.glob(f"{TEMP_FILE_PREFIX}*.mid"):
            try:
                # 取得檔案最後修改時間
                file_age = now - file_path.stat().st_mtime
                
                if file_age > CLEANUP_THRESHOLD_SECONDS:
                    file_path.unlink()
                    count += 1
                    logger.debug(f"🗑️ 已刪除過期暫存檔: {file_path.name}")
            except Exception as e:
                logger.error(f"❌ 無法刪除檔案 {file_path}: {e}")
                
        if count > 0:
            logger.info(f"✅ 清理完成，共刪除 {count} 個過期暫存檔。")
        else:
            logger.info("ℹ️ 掃描完成，未發現過期暫存檔。")
            
    except Exception as e:
        logger.error(f"❌ 執行清理任務時發生錯誤: {e}")

async def start_cleanup_task():
    """
    背景循環任務：定時執行清理邏輯。
    使用 asyncio.to_thread 避免同步 I/O 阻塞 event loop。
    """
    logger.info("🚀 背景清理任務已啟動。")
    # 啟動時先執行一次，清理上次關機留下的檔案
    await asyncio.to_thread(cleanup_old_temp_files)

    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        await asyncio.to_thread(cleanup_old_temp_files)

