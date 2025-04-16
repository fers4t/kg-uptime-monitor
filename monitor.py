import requests
import time
import yaml
import logging
import os
import platform
import schedule
import json
from datetime import datetime

class RailwayJSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "msg": record.getMessage(),
            "level": record.levelname.lower(),
            "timestamp": self.formatTime(record),
            "logger": record.name
        }
        return json.dumps(log_obj, ensure_ascii=False)

# Loglama ayarları
handler = logging.StreamHandler()
handler.setFormatter(RailwayJSONFormatter())
logger = logging.getLogger("SystemMonitor")
logger.setLevel(logging.INFO)
logger.handlers = [handler]

class SystemMonitor:
    def __init__(self, config_path="config.yaml"):
        """
        Sistem izleme uygulaması için başlatıcı fonksiyon
        
        Args:
            config_path (str): Yapılandırma dosyasının yolu
        """
        self.config = self.load_config(config_path)
        self.targets = self.config.get("targets", [])
        self.telegram_bot_token = self.config.get("telegram_bot_token", "")
        self.telegram_chat_id = self.config.get("telegram_chat_id", "")
        self.check_interval = self.config.get("check_interval", 60)  # Saniye cinsinden kontrol aralığı
        self.timeout = self.config.get("timeout", 10)  # İstek zaman aşımı süresi
        self.status = {}  # Hedef sistemlerin durumlarını saklar
        
        # Her hedefin başlangıç durumunu ayarla
        for target in self.targets:
            target_id = target.get("id", target.get("url", "unknown"))
            self.status[target_id] = {
                "last_status": "unknown",
                "last_check": None,
                "failures": 0
            }
        
        logger.info(f"Sistem İzleme Uygulaması başlatıldı. İşletim sistemi: {platform.system()}")
        
    def load_config(self, config_path):
        """
        YAML yapılandırma dosyasını yükler veya çevre değişkenlerini kullanır
        
        Args:
            config_path (str): Yapılandırma dosyasının yolu
            
        Returns:
            dict: Yapılandırma ayarları
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                logger.info(f"Yapılandırma dosyası başarıyla yüklendi: {config_path}")
                return config
        except Exception as e:
            logger.error(f"Yapılandırma dosyası yüklenirken hata oluştu: {e}")
            logger.info("Varsayılan yapılandırma kullanılıyor")
            return {
                "targets": [],
                "telegram_bot_token": "",
                "telegram_chat_id": "",
                "check_interval": 60,
                "timeout": 10
            }
            
    def check_target(self, target):
        """
        Belirtilen hedefin durumunu kontrol eder
        
        Args:
            target (dict): Kontrol edilecek hedef sistemin bilgileri
            
        Returns:
            bool: Hedef sistem ulaşılabilir ise True, değilse False
        """
        url = target.get("url", "")
        method = target.get("method", "GET")
        headers = target.get("headers", {})
        target_id = target.get("id", url)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout
            )
            
            status_code = response.status_code
            expected_status = target.get("expected_status_code", 200)
            
            if status_code == expected_status:
                logger.debug(json.dumps({
                    "msg": f"Hedef {target_id} ulaşılabilir",
                    "level": "debug",
                    "target_id": target_id,
                    "status_code": status_code
                }, ensure_ascii=False))
                
                if self.status[target_id]["last_status"] == "down":
                    recovery_time = datetime.now()
                    downtime = (recovery_time - self.status[target_id]["last_check"]).total_seconds()
                    message = f"✅ SİSTEM TEKRAR ÇALIŞIYOR\n\n"\
                              f"Hedef: {target_id}\n"\
                              f"URL: {url}\n"\
                              f"Durum Kodu: {status_code}\n"\
                              f"Kesinti Süresi: {int(downtime)} saniye\n"\
                              f"Kurtarma Zamanı: {recovery_time.strftime('%H:%M:%S %d-%m-%Y')}"
                    self.send_telegram_message(message)
                    logger.info(json.dumps({
                        "msg": f"Sistem tekrar çalışıyor: {target_id}",
                        "level": "info",
                        "target_id": target_id,
                        "downtime_seconds": int(downtime),
                        "recovery_time": recovery_time.strftime('%H:%M:%S %d-%m-%Y')
                    }, ensure_ascii=False))
                
                self.status[target_id]["last_status"] = "up"
                self.status[target_id]["failures"] = 0
                return True
            else:
                logger.warning(json.dumps({
                    "msg": f"Hedef {target_id} beklenmeyen durum kodu döndürdü: {status_code}",
                    "level": "warn",
                    "target_id": target_id,
                    "status_code": status_code,
                    "expected_status": expected_status
                }, ensure_ascii=False))
                return False
                
        except requests.RequestException as e:
            logger.error(json.dumps({
                "msg": f"Hedef {target_id} kontrol edilirken hata oluştu: {str(e)}",
                "level": "error",
                "target_id": target_id,
                "error": str(e)
            }, ensure_ascii=False))
            return False
    
    def send_telegram_message(self, message):
        """
        Telegram üzerinden bildirim gönderir
        
        Args:
            message (str): Gönderilecek mesaj
            
        Returns:
            bool: Mesaj başarıyla gönderildi ise True, gönderilemediyse False
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning(json.dumps({
                "msg": "Telegram bilgileri eksik. Bildirim gönderilemiyor.",
                "level": "warn"
            }, ensure_ascii=False))
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(json.dumps({
                    "msg": "Telegram bildirimi başarıyla gönderildi",
                    "level": "info"
                }, ensure_ascii=False))
                return True
            else:
                logger.error(json.dumps({
                    "msg": f"Telegram bildirimi gönderilirken hata oluştu: {response.text}",
                    "level": "error",
                    "response_text": response.text,
                    "status_code": response.status_code
                }, ensure_ascii=False))
                return False
                
        except Exception as e:
            logger.error(json.dumps({
                "msg": f"Telegram bildirimi gönderilirken istisna oluştu: {str(e)}",
                "level": "error",
                "error": str(e)
            }, ensure_ascii=False))
            return False
    
    def check_all_targets(self):
        """
        Tüm hedeflerin durumunu kontrol eder ve gerekirse bildirim gönderir
        """
        logger.info(json.dumps({
            "msg": "Tüm hedefler kontrol ediliyor...",
            "level": "info"
        }, ensure_ascii=False))
        
        for target in self.targets:
            target_id = target.get("id", target.get("url", "unknown"))
            current_time = datetime.now()
            
            is_available = self.check_target(target)
            self.status[target_id]["last_check"] = current_time
            
            if not is_available:
                self.status[target_id]["failures"] += 1
                failure_threshold = target.get("failure_threshold", 3)
                
                if self.status[target_id]["failures"] >= failure_threshold:
                    if self.status[target_id]["last_status"] != "down":
                        message = f"🔴 SİSTEM ÇALIŞMIYOR\n\n"\
                                  f"Hedef: {target_id}\n"\
                                  f"URL: {target.get('url', '')}\n"\
                                  f"Zaman: {current_time.strftime('%H:%M:%S %d-%m-%Y')}\n"\
                                  f"Başarısız Deneme: {self.status[target_id]['failures']}"
                        
                        self.send_telegram_message(message)
                        self.status[target_id]["last_status"] = "down"
                        logger.error(json.dumps({
                            "msg": f"Hedef {target_id} çalışmıyor! Bildirim gönderildi.",
                            "level": "error",
                            "target_id": target_id,
                            "failures": self.status[target_id]['failures'],
                            "time": current_time.strftime('%H:%M:%S %d-%m-%Y')
                        }, ensure_ascii=False))
                else:
                    logger.warning(json.dumps({
                        "msg": f"Hedef {target_id} kontrolü başarısız",
                        "level": "warn",
                        "target_id": target_id,
                        "failures": self.status[target_id]['failures']
                    }, ensure_ascii=False))
            else:
                logger.info(json.dumps({
                    "msg": f"Hedef {target_id} başarıyla kontrol edildi",
                    "level": "info",
                    "target_id": target_id,
                    "status": "up"
                }, ensure_ascii=False))
    
    def run(self):
        """
        Uygulamayı belirtilen aralıklarla çalıştırır
        """
        self.check_all_targets()
        schedule.every(self.check_interval).seconds.do(self.check_all_targets)
        
        logger.info(json.dumps({
            "msg": f"Sistem izleme çalışıyor. Kontrol aralığı: {self.check_interval} saniye",
            "level": "info",
            "check_interval": self.check_interval
        }, ensure_ascii=False))
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info(json.dumps({
                "msg": "Uygulama kullanıcı tarafından durduruldu.",
                "level": "info"
            }, ensure_ascii=False))
        except Exception as e:
            logger.error(json.dumps({
                "msg": f"Uygulama çalışırken hata oluştu: {str(e)}",
                "level": "error",
                "error": str(e)
            }, ensure_ascii=False))

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.run()