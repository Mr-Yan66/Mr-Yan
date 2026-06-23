"""
Robot Trading Forex WeltTrader - Système Expert
Analyse automatique du marché 24/7 avec signaux visuels et trading automatique
"""

import json
import time
from datetime import datetime, timedelta
from analysis import TrendAnalyzer, SignalGenerator
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self, config_file='config.json'):
        """Initialise le robot trading"""
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        self.analyzer = TrendAnalyzer(self.config)
        self.signal_gen = SignalGenerator(self.config)
        self.last_check = {}
        self.active = True
        
        logger.info("🤖 Robot Trading initialisé")
        logger.info(f"Paires Forex: {self.config['forex_pairs']}")
    
    def fetch_market_data(self, pair, timeframe):
        """
        Récupère les données du marché depuis WeltTrader
        pair: Ex 'EURUSD'
        timeframe: 5, 15, 30 (minutes)
        """
        try:
            # Import conditionnel pour WeltTrader
            import metatrader5 as mt5
            
            if not mt5.initialize():
                logger.error(f"❌ Erreur de connexion MT5 pour {pair}")
                return None
            
            # Récupération des données
            rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_M5 if timeframe == 5 
                                           else mt5.TIMEFRAME_M15 if timeframe == 15
                                           else mt5.TIMEFRAME_M30, 
                                           0, 100)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"⚠️ Pas de données pour {pair}")
                return None
            
            # Conversion en DataFrame
            import pandas as pd
            df = pd.DataFrame(rates)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            mt5.shutdown()
            return df
            
        except ImportError:
            logger.error("❌ MetaTrader5 non installé. Utilisation de données de test...")
            return self._generate_test_data(pair)
    
    def _generate_test_data(self, pair):
        """Génère des données de test pour démonstration"""
        import pandas as pd
        import numpy as np
        
        prices = [1.0850 + np.random.uniform(-0.0005, 0.0005) for _ in range(100)]
        data = {
            'close': prices,
            'high': [p + 0.0003 for p in prices],
            'low': [p - 0.0003 for p in prices]
        }
        return pd.DataFrame(data)
    
    def analyze_market(self, pair):
        """Analyse complète du marché pour une paire"""
        logger.info(f"📊 Analyse du marché: {pair}")
        
        # Récupération des données
        market_data = self.fetch_market_data(pair, 15)
        if market_data is None:
            return None
        
        # Analyse des tendances
        trend_analysis = self.analyzer.identify_trend_zones(market_data)
        
        if trend_analysis is None:
            return None
        
        # Génération du signal visuel
        signal = self.signal_gen.generate_visual_signal(trend_analysis)
        
        # Génération du rapport
        report = self.signal_gen.generate_report(pair, trend_analysis, signal)
        
        return {
            'pair': pair,
            'signal': signal,
            'analysis': trend_analysis,
            'report': report,
            'timestamp': datetime.now()
        }
    
    def display_signal(self, result):
        """Affiche le signal visuel clignotant"""
        if result is None:
            return
        
        signal = result['signal']
        analysis = result['analysis']
        pair = result['pair']
        
        # Signal clignotant
        colors = {
            'BLEU': '🔵',
            'ROUGE': '🔴',
            'JAUNE': '🟡'
        }
        
        emoji = colors.get(signal['color'], '⚪')
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{emoji} PAIRE: {pair} - {signal['color']}")
        logger.info(f"{'='*60}")
        logger.info(f"Signal: {signal['signal']}")
        logger.info(f"Force: {analysis['strength']:.1f}%")
        logger.info(f"Direction: {analysis['direction']}")
        logger.info(f"Durée estimée: {analysis['duration_minutes']} minutes")
        logger.info(f"Recommandation: {self.signal_gen._get_recommendation(analysis)}")
        
        if not analysis['is_good_market']:
            logger.warning(f"⏳ Marché faible - Prochaine vérification dans 30 minutes")
        else:
            logger.info(f"✅ Marché opportun - PRÊT POUR LE TRADING")
        
        logger.info(f"Support: {analysis['support']}")
        logger.info(f"Résistance: {analysis['resistance']}")
        logger.info(f"{'='*60}\n")
    
    def should_trade(self, result):
        """Détermine si on doit trader basé sur l'analyse"""
        if result is None:
            return False, "Pas d'analyse"
        
        analysis = result['analysis']
        
        if not analysis['is_good_market']:
            return False, f"Marché trop faible ({analysis['strength']:.1f}%)"
        
        if analysis['direction'] in ['HAUT', 'BAS']:
            return True, analysis['direction']
        
        return False, "Signal indécis"
    
    def execute_trade(self, pair, direction):
        """Exécute une transaction de trading automatique"""
        logger.info(f"\n🚀 EXÉCUTION DU TRADE")
        logger.info(f"Paire: {pair}")
        logger.info(f"Direction: {direction}")
        
        try:
            import metatrader5 as mt5
            
            if not mt5.initialize():
                logger.error("❌ Erreur de connexion MT5")
                return False
            
            # Préparation de l'ordre
            symbol = pair
            if direction == 'HAUT':
                order_type = mt5.ORDER_TYPE_BUY
                action = mt5.TRADE_ACTION_DEAL
                logger.info("📈 Signal ACHAT - Préparation de l'ordre BUY")
            else:
                order_type = mt5.ORDER_TYPE_SELL
                action = mt5.TRADE_ACTION_DEAL
                logger.info("📉 Signal VENTE - Préparation de l'ordre SELL")
            
            # Configuration des paramètres
            price = mt5.symbol_info_tick(symbol).ask if direction == 'HAUT' else mt5.symbol_info_tick(symbol).bid
            lot = 0.1  # Volume
            
            request = {
                "action": action,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"Robot Trading - {direction}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Envoi de l'ordre
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Erreur trade: {result.comment}")
                return False
            
            logger.info(f"✅ Trade exécuté avec succès!")
            logger.info(f"Order Ticket: {result.order}")
            
            mt5.shutdown()
            return True
            
        except ImportError:
            logger.warning("⚠️ Mode simulation - Trade exécuté en simulation")
            logger.info(f"✅ [SIMULATION] Trade {direction} exécuté pour {pair}")
            return True
    
    def run(self):
        """Lance le robot en mode continu"""
        logger.info("\n🚀 DÉMARRAGE DU ROBOT TRADING")
        logger.info(f"⏰ Heure: {datetime.now()}")
        logger.info("="*60)
        
        try:
            iteration = 0
            while self.active:
                iteration += 1
                logger.info(f"\n📍 Cycle #{iteration} - {datetime.now()}")
                
                # Analyse de chaque paire
                for pair in self.config['forex_pairs']:
                    # Vérification du délai d'attente
                    if pair in self.last_check:
                        time_since_check = datetime.now() - self.last_check[pair]
                        if time_since_check.total_seconds() < 1800:  # 30 minutes
                            logger.info(f"⏸️  {pair} - En attente... ({int(time_since_check.total_seconds()/60)} min)")
                            continue
                    
                    # Analyse du marché
                    result = self.analyze_market(pair)
                    self.display_signal(result)
                    
                    # Vérification si on doit trader
                    should_trade, reason = self.should_trade(result)
                    
                    if should_trade:
                        logger.info(f"✅ Condition de trading remplie: {reason}")
                        self.execute_trade(pair, reason)
                        self.last_check[pair] = datetime.now()
                    else:
                        logger.info(f"⏳ Pas de trade: {reason}")
                        if result and not result['analysis']['is_good_market']:
                            self.last_check[pair] = datetime.now()
                
                # Attendre avant le prochain cycle
                logger.info("\n⏳ En attente de 5 minutes avant le prochain scan...")
                time.sleep(300)  # 5 minutes
                
        except KeyboardInterrupt:
            logger.info("\n⛔ Robot arrêté par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur: {str(e)}", exc_info=True)
        finally:
            logger.info("\n🛑 Arrêt du robot trading")


def main():
    """Point d'entrée principal"""
    logger.info("╔" + "="*58 + "╗")
    logger.info("║" + " "*10 + "ROBOT TRADING FOREX - WELTRADER" + " "*16 + "║")
    logger.info("║" + " "*15 + "Analyse Expert du Marché 24/7" + " "*13 + "║")
    logger.info("╚" + "="*58 + "╝")
    
    # Créer et démarrer le robot
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
