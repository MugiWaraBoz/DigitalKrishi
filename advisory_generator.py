# -*- coding: utf-8 -*-

class AgriculturalAdvisoryGenerator:
    """Generates concise, actionable crop advisories in Bangla.

    The generator follows the user's rules: crop-specific advice, action+reason
    in Bangla, concise length (2-5 lines), and `console.log` SMS alerts for
    Critical risk.
    """

    def _map_vulnerability(self, crop: str, condition: str) -> str:
        c = (crop or '').strip()
        w = (condition or '').lower()
        if 'বৃষ্টি' in w or 'বর্ষণ' in w or 'rain' in w:
            return 'বৃষ্টি/আর্দ্রতার কারণে ফাঙ্গাস বা পচনের ঝুঁকি'
        if 'আর্দ্র' in w or 'humidity' in w:
            return 'উচ্চ আর্দ্রতায় ছত্রাকের ঝুঁকি'
        if 'গরম' in w or 'তাপ' in w or 'heat' in w:
            return 'উচ্চ তাপের কারণে তাপ-স্ট্রেস'
        if 'ঝড়' in w or 'storm' in w:
            return 'ঝড়/বাতাসে ভাঙ্গার ঝুঁকি'
        return 'স্বাভাবিক অবস্থায় পর্যবেক্ষণ প্রয়োজন'

    def generate_crops_advisory(self, crops, weather: dict, season: str = None, risk_override: str = None):
        """Return list of short Bangla advisory strings, one per crop.

        Args:
            crops (list): crop names (Bangla or English)
            weather (dict): keys: temperature, humidity, rain_chance, condition
            season (str): optional season token
            risk_override (str): optional risk ('Low','Moderate','High','Critical')
        """
        advisories = []

        # Normalize weather
        temp = float(weather.get('temperature') or weather.get('temp') or 25)
        humidity = float(weather.get('humidity') or 0)
        rain = float(weather.get('rain_chance') or weather.get('rain') or weather.get('rainfall') or 0)
        condition = (weather.get('condition') or '').lower()

        for crop in (crops or []):
            c = (crop or '').strip()
            if not c:
                continue

            # Determine risk
            if risk_override:
                risk = str(risk_override).capitalize()
            else:
                if rain > 70 or humidity > 90 or temp > 42:
                    risk = 'Critical'
                elif rain > 50 or humidity > 85 or temp > 36:
                    risk = 'High'
                elif rain > 25 or humidity > 75 or temp > 32:
                    risk = 'Moderate'
                else:
                    risk = 'Low'

            vuln = self._map_vulnerability(c, condition)

            lines = []
            sms = None

            # Crop-specific actionable advice (action + reason)
            key = c.lower()

            # Potato
            if 'আলু' in key or 'potato' in key:
                if risk == 'Critical' or (humidity > 88 and rain > 60):
                    lines.append('তীব্র সতর্কতা: আলুর গুদামে পচা ও ছত্রাকের ঝুঁকি উচ্চ; এখনই ভেন্টিলেশন বাড়ান।')
                    sms = "console.log('SMS ALERT: আলু গুদামে পচা ঝুঁকি, দ্রুত ব্যবস্থা নিন।');"
                elif risk == 'High' or humidity > 80:
                    lines.append('আলুর গুদামে আর্দ্রতা বেশি; ফ্যান চালু করে বায়ু চলাচল বাড়ান।')
                elif risk == 'Moderate':
                    lines.append('আর্দ্রতা বাড়ছে; পচা অংশ আলাদা করে রাখুন ও বায়ু বাড়ান।')
                else:
                    lines.append('আলু ভাল আছে; শুকনো পরিবেশ বজায় রাখুন।')

            # Corn / Maize
            elif 'ভুট্টা' in key or 'maize' in key or 'corn' in key:
                if risk == 'Critical' or temp > 40:
                    lines.append('তীব্র তাপ/শুকনো: ভুট্টা ঝুঁকিতে; দ্রুত সেচ দিন বা ছায়া দিন।')
                    sms = "console.log('SMS ALERT: ভুট্টা তাপে ঝুঁকিতে, সেচ/ছায়া দিন।');"
                elif risk == 'High' or temp > 36:
                    lines.append('তাপ বৃদ্ধি; নিয়মিত সেচ ও বিকালে ছায়া দিন।')
                elif risk == 'Moderate':
                    lines.append('শুকনো ঝুঁকি আছে; সেচ পরিকল্পনা প্রস্তুত রাখুন।')
                else:
                    lines.append('ভুট্টা স্বাভাবিক; পর্যবেক্ষণ চালিয়ে যান।')

            # Paddy / Rice
            elif 'ধান' in key or 'paddy' in key or 'rice' in key:
                if risk == 'Critical' or rain > 80:
                    lines.append('জরুরি: ভারী বৃষ্টি/জমে থাকা পানি; এখনই নিকাশপথ খুলুন ও পানি সরান।')
                    sms = "console.log('SMS ALERT: ধান জমে আছে, পানি নিষ্কাশন করুন।');"
                elif risk == 'High' or rain > 60:
                    lines.append('ভারী বৃষ্টির আশঙ্কা; নিকাশপথ ও জমির অবস্থা যাচাই করুন।')
                elif risk == 'Moderate':
                    lines.append('বৃষ্টি বাড়তে পারে; নিকাশপথ পরিষ্কার রাখুন।')
                else:
                    lines.append('ধান স্বাভাবিক; নিকাশ ও পর্যবেক্ষণ বজায় রাখুন।')

            # Tomato
            elif 'টমেটো' in key or 'tomato' in key:
                if risk == 'Critical' or temp > 40:
                    lines.append('তীব্র তাপ: টমেটো ঝুলে পড়তে পারে; দ্রুত ছায়া দিন ও সেচ বাড়ান।')
                    sms = "console.log('SMS ALERT: টমেটো তাপ-স্ট্রেস, ছায়া ও পানি দিন।');"
                elif risk == 'High' or temp > 36:
                    lines.append('তাপ বেশি; বিকালে ছায়া ও সেচ দিন।')
                elif risk == 'Moderate':
                    lines.append('ফসল পর্যবেক্ষণ করুন ও বিকালে হালকা সেচ দিন।')
                else:
                    lines.append('টমেটো ভালো চলছে; নিয়মিত পানি ও পরিচর্যা দিন।')

            # Onion
            elif 'পেঁয়াজ' in key or 'onion' in key:
                if risk == 'Critical' or (humidity > 85 and rain > 50):
                    lines.append('তীব্র আর্দ্রতা: পেঁয়াজে পচা বাড়বে; দ্রুত জমি/সংরক্ষণ স্থান শুকিয়ে নিন।')
                    sms = "console.log('SMS ALERT: পেঁয়াজ পচা ঝুঁকি, জায়গা শুকিয়ে দিন।');"
                elif risk == 'High' or humidity > 80:
                    lines.append('আর্দ্রতা বেশি; সংরক্ষণস্থলে বাতাস চলাচল বাড়ান।')
                elif risk == 'Moderate':
                    lines.append('ভেজা মাটি আছে; শুকানোর ব্যবস্থা রাখুন।')
                else:
                    lines.append('পেঁয়াজ ঠিক আছে; শুকনো পরিবেশ বজায় রাখুন।')

            else:
                # Generic fallback
                if risk == 'Critical':
                    lines.append(f'জরুরি: {c} তীব্র ঝুঁকিতে। দ্রুত সুরক্ষা নিন।')
                    sms = f"console.log('SMS ALERT: {c} তীব্র ঝুঁকি, দ্রুত ব্যবস্থা নিন।');"
                elif risk == 'High':
                    lines.append(f'{c} উচ্চ ঝুঁকিতে আছে; অবিলম্বে ব্যবস্থা নিন।')
                elif risk == 'Moderate':
                    lines.append(f'{c} সতর্ক করুন; পর্যবেক্ষণ বাড়ান।')
                else:
                    lines.append(f'{c} স্বাভাবিক; নিয়মিত পরিচর্যা চালান।')

            # Optional harvest hint (short)
            season_lower = (season or '').lower() if season else ''
            if season_lower in ['harvest', 'kharif', 'rabi', 'autumn', 'fall'] and risk in ['Low', 'Moderate']:
                lines.append('ফসল পরিপক্ক হলে সংগ্রহ বিবেচনা করুন।')
            elif risk in ['High']:
                lines.append('পরিপক্ক হলে এখনই সংগ্রহ বিবেচনা করুন।')

            # Build final advisory: header + up to 3 lines to keep short
            advisory_lines = lines[:3]
            header = f"{c} — ঝুঁকি: {risk}"
            advisory_text = header + '\n' + '\n'.join(advisory_lines)
            if sms:
                advisory_text = advisory_text + '\n\n' + sms

            advisories.append(advisory_text)

        return advisories


if __name__ == '__main__':
    g = AgriculturalAdvisoryGenerator()
    sample = g.generate_crops_advisory(['আলু','টমেটো','ধান'], {'temperature':28,'humidity':85,'rain_chance':70})
    for a in sample:
        print('---')
        print(a)

