import requests
import time
import yaml
import logging
import os
import platform
import schedule
from datetime import datetime

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SystemMonitor")

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
        YAML yapılandırma dosyasını yükler
        
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
            
            # İsteğin başarılı olup olmadığını kontrol et
            status_code = response.status_code
            expected_status = target.get("expected_status_code", 200)
            
            if status_code == expected_status:
                logger.debug(f"Hedef {target_id} ulaşılabilir. Durum kodu: {status_code}")
                
                # Eğer sistem daha önce çalışmıyorsa ve şimdi çalışıyorsa, iyileşme bildirimi gönder
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
                
                self.status[target_id]["last_status"] = "up"
                self.status[target_id]["failures"] = 0
                return True
            else:
                logger.warning(f"Hedef {target_id} beklenmeyen durum kodu döndürdü: {status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Hedef {target_id} kontrol edilirken hata oluştu: {e}")
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
            logger.warning("Telegram bilgileri eksik. Bildirim gönderilemiyor.")
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
                logger.info("Telegram bildirimi başarıyla gönderildi")
                return True
            else:
                logger.error(f"Telegram bildirimi gönderilirken hata oluştu: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram bildirimi gönderilirken istisna oluştu: {e}")
            return False
    
    def check_all_targets(self):
        """
        Tüm hedeflerin durumunu kontrol eder ve gerekirse bildirim gönderir
        """
        logger.info("Tüm hedefler kontrol ediliyor...")
        
        for target in self.targets:
            target_id = target.get("id", target.get("url", "unknown"))
            current_time = datetime.now()
            
            # Hedefi kontrol et
            is_available = self.check_target(target)
            
            # Son kontrol zamanını güncelle
            self.status[target_id]["last_check"] = current_time
            
            if not is_available:
                # Başarısız kontrol sayısını artır
                self.status[target_id]["failures"] += 1
                
                # Yapılandırma dosyasından veya varsayılan olarak 3 başarısız deneme sonrası bildirim gönder
                failure_threshold = target.get("failure_threshold", 3)
                
                if self.status[target_id]["failures"] >= failure_threshold:
                    if self.status[target_id]["last_status"] != "down":
                        # Durum değişti, bildirim gönder
                        message = f"🔴 SİSTEM ÇALIŞMIYOR\n\n"\
                                  f"Hedef: {target_id}\n"\
                                  f"URL: {target.get('url', '')}\n"\
                                  f"Zaman: {current_time.strftime('%H:%M:%S %d-%m-%Y')}\n"\
                                  f"Başarısız Deneme: {self.status[target_id]['failures']}"
                        
                        self.send_telegram_message(message)
                        self.status[target_id]["last_status"] = "down"
                        logger.warning(f"Hedef {target_id} çalışmıyor! Bildirim gönderildi.")
                else:
                    logger.warning(f"Hedef {target_id} kontrolü başarısız. Başarısız deneme sayısı: {self.status[target_id]['failures']}")
            else:
                # Hedef çalışıyor
                self.status[target_id]["last_status"] = "up"
                logger.info(f"Hedef {target_id} başarıyla kontrol edildi. Sistem çalışıyor.")
    
    def run(self):
        """
        Uygulamayı belirtilen aralıklarla çalıştırır
        """
        # İlk kez hemen kontrol et
        self.check_all_targets()
        
        # Düzenli kontroller için zamanlama
        schedule.every(self.check_interval).seconds.do(self.check_all_targets)
        
        logger.info(f"Sistem izleme çalışıyor. Kontrol aralığı: {self.check_interval} saniye")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Uygulama kullanıcı tarafından durduruldu.")
        except Exception as e:
            logger.error(f"Uygulama çalışırken hata oluştu: {e}")

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.run()