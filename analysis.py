"""
Module d'analyse des tendances du marché Forex
Identifie les zones de support/résistance et prédit la direction
"""

import numpy as np
import pandas as pd
from scipy import signal
from datetime import datetime, timedelta
import json

class TrendAnalyzer:
    def __init__(self, config):
        self.config = config
        self.min_strength = config['analysis']['min_strength_percentage']
        
    def identify_trend_zones(self, price_data):
        """
        Identifie les zones de tendance et trace les lignes d'analyse
        Retourne: direction (HAUT/BAS), force (%), durée estimée
        """
        if len(price_data) < 20:
            return None
            
        closes = price_data['close'].values
        highs = price_data['high'].values
        lows = price_data['low'].values
        
        # Calcul des supports et résistances
        resistance_lines = self._find_resistance(highs)
        support_lines = self._find_support(lows)
        
        # Analyse de la tendance avec moyenne mobile
        trend_direction = self._analyze_trend_direction(closes)
        trend_strength = self._calculate_trend_strength(closes)
        trend_duration = self._estimate_trend_duration(closes)
        
        return {
            'direction': trend_direction,  # 'HAUT' (bleu) ou 'BAS' (rouge)
            'strength': trend_strength,      # 0-100%
            'duration_minutes': trend_duration,
            'resistance': resistance_lines,
            'support': support_lines,
            'is_good_market': trend_strength >= self.min_strength,
            'next_check': datetime.now() + timedelta(minutes=30) if trend_strength < self.min_strength else None
        }
    
    def _find_resistance(self, highs, num_levels=3):
        """Identifie les niveaux de résistance"""
        peaks, _ = signal.find_peaks(highs, distance=5)
        if len(peaks) > 0:
            top_peaks = sorted(peaks, key=lambda i: highs[i], reverse=True)[:num_levels]
            return [float(highs[i]) for i in top_peaks]
        return []
    
    def _find_support(self, lows, num_levels=3):
        """Identifie les niveaux de support"""
        valleys, _ = signal.find_peaks(-lows, distance=5)
        if len(valleys) > 0:
            bottom_valleys = sorted(valleys, key=lambda i: lows[i])[:num_levels]
            return [float(lows[i]) for i in bottom_valleys]
        return []
    
    def _analyze_trend_direction(self, closes):
        """Détermine si le marché monte (HAUT/bleu) ou descend (BAS/rouge)"""
        # Moyenne mobile exponentielle 9 et 21
        ema9 = self._calculate_ema(closes, 9)
        ema21 = self._calculate_ema(closes, 21)
        
        current_price = closes[-1]
        ema9_last = ema9[-1] if len(ema9) > 0 else current_price
        ema21_last = ema21[-1] if len(ema21) > 0 else current_price
        
        if ema9_last > ema21_last and current_price > ema9_last:
            return 'HAUT'  # Bleu - Signal de hausse
        elif ema9_last < ema21_last and current_price < ema9_last:
            return 'BAS'   # Rouge - Signal de baisse
        else:
            return 'INDECIS'
    
    def _calculate_trend_strength(self, closes, period=14):
        """Calcule la force de la tendance en pourcentage (0-100%)"""
        if len(closes) < period:
            return 0
            
        gains = np.maximum(np.diff(closes), 0)
        losses = np.maximum(-np.diff(closes), 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            rsi = 100 if avg_gain > 0 else 50
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Convertir RSI en force de tendance (0-100%)
        strength = abs(rsi - 50) * 2
        return min(100, max(0, strength))
    
    def _estimate_trend_duration(self, closes, period=20):
        """Estime la durée probable de la tendance en minutes"""
        if len(closes) < period:
            return 30
        
        # Volatilité
        returns = np.diff(closes) / closes[:-1]
        volatility = np.std(returns[-period:])
        
        # Durée estimée (moins volatil = plus long)
        if volatility < 0.0005:
            return 120  # 2 heures
        elif volatility < 0.001:
            return 60   # 1 heure
        elif volatility < 0.002:
            return 30   # 30 minutes
        else:
            return 15   # 15 minutes
    
    def _calculate_ema(self, prices, period):
        """Calcul de la moyenne mobile exponentielle"""
        if len(prices) < period:
            return prices
        
        ema = np.zeros_like(prices, dtype=float)
        sma = np.mean(prices[:period])
        ema[period - 1] = sma
        
        multiplier = 2.0 / (period + 1)
        
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
        
        return ema
    
    def should_wait_30_minutes(self, trend_analysis):
        """Détermine si on doit attendre 30 minutes avant de trader"""
        if not trend_analysis:
            return True
        
        return trend_analysis['strength'] < self.min_strength


class SignalGenerator:
    def __init__(self, config):
        self.config = config
    
    def generate_visual_signal(self, trend_analysis):
        """Génère le signal visuel clignotant (BLEU/ROUGE)"""
        if trend_analysis['direction'] == 'HAUT':
            return {
                'color': 'BLEU',
                'emoji': '🔵',
                'signal': 'ACHAT - Marché haussier',
                'blink': True
            }
        elif trend_analysis['direction'] == 'BAS':
            return {
                'color': 'ROUGE',
                'emoji': '🔴',
                'signal': 'VENTE - Marché baissier',
                'blink': True
            }
        else:
            return {
                'color': 'JAUNE',
                'emoji': '🟡',
                'signal': 'EN ATTENTE - Signal indécis',
                'blink': False
            }
    
    def generate_report(self, pair, trend_analysis, signal):
        """Génère un rapport d'analyse complet"""
        report = {
            'pair': pair,
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'trend': trend_analysis,
            'recommendation': self._get_recommendation(trend_analysis)
        }
        return report
    
    def _get_recommendation(self, analysis):
        """Recommandation de trading basée sur l'analyse"""
        if analysis['strength'] < 40:
            return "ATTENDRE 30 MINUTES - Marché trop faible"
        elif analysis['strength'] < 65:
            return "MARCHÉ FAIBLE - Attendre renforcement"
        elif analysis['direction'] == 'HAUT':
            return f"ACHAT RECOMMANDÉ - Force: {analysis['strength']:.1f}% - Durée: {analysis['duration_minutes']} min"
        elif analysis['direction'] == 'BAS':
            return f"VENTE RECOMMANDÉE - Force: {analysis['strength']:.1f}% - Durée: {analysis['duration_minutes']} min"
        else:
            return "ATTENDRE CLARIFICATION DU SIGNAL"
