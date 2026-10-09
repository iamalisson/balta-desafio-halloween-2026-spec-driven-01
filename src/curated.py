"""Hand-curated data where no open string source exists. Every row here is tagged `curated` in Anki."""

# Android Settings / quick-settings labels, most-used first. English must match AOSP en strings exactly
# (the Chinese comes from AOSP zh-rCN, so it is official); unmatched labels are printed by the build.
ANDROID_SEEDS = """Network & internet|Wi-Fi|Bluetooth|Mobile network|Mobile data|Airplane mode|Hotspot & tethering|
Connected devices|Apps|Notifications|Battery|Battery Saver|Storage|Sound & vibration|Volume|Vibrate|Display|
Brightness level|Dark theme|Auto-rotate|Screen timeout|Font size|Display size|Night Light|Wallpaper & style|
Accessibility|Security & privacy|Screen lock|Location|Safety & emergency|Passwords & accounts|System|Languages|
Language|Keyboard|Date & time|Time zone|Use 24-hour format|Backup|Reset options|Restart|Flashlight|Do Not Disturb|
Screen record|Screenshot|Cast|Alarm|Default apps|App info|Permission manager|Force stop|Uninstall|Clear storage|
Clear cache|Internet""".replace("\n", "").split("|")

# iOS 18 zh-CN labels written from memory: UNVERIFIED. Check them on the iPhone after switching it to Chinese
# and fix any row that differs (then rebuild + re-import).
IOS = [
    ("Settings", "设置"), ("General", "通用"), ("About", "关于本机"), ("Software Update", "软件更新"),
    ("Wi-Fi", "无线局域网"), ("Bluetooth", "蓝牙"), ("Cellular", "蜂窝网络"), ("Personal Hotspot", "个人热点"),
    ("Airplane Mode", "飞行模式"), ("Notifications", "通知"), ("Sounds & Haptics", "声音与触感"),
    ("Focus", "专注模式"), ("Do Not Disturb", "勿扰模式"), ("Screen Time", "屏幕使用时间"),
    ("Control Center", "控制中心"), ("Display & Brightness", "显示与亮度"), ("Accessibility", "辅助功能"),
    ("Wallpaper", "墙纸"), ("StandBy", "待机显示"), ("Face ID & Passcode", "面容ID与密码"),
    ("Touch ID & Passcode", "触控ID与密码"), ("Emergency SOS", "SOS紧急联络"), ("Battery", "电池"),
    ("Low Power Mode", "低电量模式"), ("Privacy & Security", "隐私与安全性"), ("Location Services", "定位服务"),
    ("Passwords", "密码"), ("Mail", "邮件"), ("Contacts", "通讯录"), ("Calendar", "日历"), ("Notes", "备忘录"),
    ("Reminders", "提醒事项"), ("Phone", "电话"), ("Messages", "信息"), ("Camera", "相机"), ("Photos", "照片"),
    ("Health", "健康"), ("Find My", "查找"), ("Files", "文件"), ("Weather", "天气"), ("Clock", "时钟"),
    ("Calculator", "计算器"), ("Compass", "指南针"), ("Translate", "翻译"), ("Language & Region", "语言与地区"),
    ("Date & Time", "日期与时间"), ("Keyboard", "键盘"), ("iPhone Storage", "iPhone储存空间"),
    ("Transfer or Reset iPhone", "传输或还原iPhone"), ("Shut Down", "关机"),
    ("Background App Refresh", "后台App刷新"), ("Auto-Lock", "自动锁定"), ("Dark", "深色"), ("Light", "浅色"),
    ("Night Shift", "夜览"), ("True Tone", "原彩显示"), ("Text Size", "文字大小"), ("Ringtone", "电话铃声"),
    ("Silent Mode", "静音模式"), ("Screen Recording", "屏幕录制"), ("Flashlight", "手电筒"),
    ("Voicemail", "语音留言"), ("Recents", "最近通话"), ("Favorites", "个人收藏"), ("Keypad", "拨号键盘"),
    ("Wallet & Apple Pay", "钱包与Apple Pay"),
]

# Everyday time words that CLDR (babel) has no field for.
DATE_WORDS = [
    ("today", "今天"), ("tomorrow", "明天"), ("yesterday", "昨天"), ("the day before yesterday", "前天"),
    ("the day after tomorrow", "后天"), ("just now", "刚刚"), ("now", "现在"), ("this week", "本周"),
    ("last week", "上周"), ("next week", "下周"), ("this month", "本月"), ("last month", "上个月"),
    ("next month", "下个月"), ("this year", "今年"), ("last year", "去年"), ("next year", "明年"),
    ("date", "日期"), ("time", "时间"), ("timer", "计时器"), ("stopwatch", "秒表"), ("weekend", "周末"),
    ("working day", "工作日"),
]

# Famous two-part allegorical sayings (歇后语): riddle —— answer. CC-CEDICT has none, so they are curated.
XIEHOUYU = [
    ("外甥打灯笼——照舅", "nephew carries a lantern: lights the uncle (照舅 sounds like 照旧) = same as before"),
    ("黄鼠狼给鸡拜年——没安好心", "weasel pays a New Year call on the hen = up to no good"),
    ("竹篮打水——一场空", "drawing water with a bamboo basket = all effort for nothing"),
    ("哑巴吃黄连——有苦说不出", "a mute eats bitter herbs = suffers but cannot complain"),
    ("小葱拌豆腐——一清二白", "scallion with tofu = perfectly clear / innocent"),
    ("肉包子打狗——有去无回", "throwing a meat bun at a dog = gone and never coming back"),
    ("猫哭耗子——假慈悲", "the cat weeps for the mouse = crocodile tears"),
    ("泥菩萨过江——自身难保", "a clay Buddha crossing a river = can't even save oneself"),
    ("丈二和尚——摸不着头脑", "a ten-foot monk: you can't reach his head = totally confused"),
    ("狗拿耗子——多管闲事", "a dog catching mice = minding other people's business"),
    ("司马昭之心——路人皆知", "Sima Zhao's ambition = an open secret"),
    ("擀面杖吹火——一窍不通", "blowing a fire through a rolling pin = knows nothing about it"),
    ("八仙过海——各显神通", "the Eight Immortals cross the sea = everyone shows their own skills"),
    ("老鼠过街——人人喊打", "a rat crossing the street = hated by everyone"),
    ("千里送鹅毛——礼轻情意重", "a goose feather sent from afar = small gift, big feelings"),
    ("芝麻开花——节节高", "sesame in bloom = getting better step by step"),
    ("骑驴看唱本——走着瞧", "reading a script on a donkey = wait and see"),
    ("秀才遇到兵——有理说不清", "a scholar meets a soldier = right but can't argue it"),
    ("姜太公钓鱼——愿者上钩", "Jiang Taigong fishing = only the willing take the bait"),
    ("鸡蛋碰石头——自不量力", "an egg hits a rock = overestimating oneself"),
    ("和尚打伞——无法无天", "a monk under an umbrella: no hair (法 sounds like 发), no sky = lawless"),
    ("孔夫子搬家——净是书", "Confucius moves house: all books (书 sounds like 输) = always losing"),
    ("飞蛾扑火——自取灭亡", "a moth flies into the flame = courting destruction"),
    ("门缝里看人——把人看扁了", "looking at someone through a door crack = underestimating them"),
    ("癞蛤蟆想吃天鹅肉——痴心妄想", "a toad wants swan meat = wishful thinking"),
    ("脱裤子放屁——多此一举", "taking off your pants to fart = completely unnecessary"),
    ("茶壶里煮饺子——有口倒不出", "dumplings in a teapot = knows it but can't say it"),
    ("瞎子点灯——白费蜡", "a blind man lights a lamp = wasted effort"),
    ("打破砂锅——问到底", "breaking a clay pot: the crack goes to the bottom (璺 sounds like 问) = ask to the very end"),
]

# The way back to English on every device: these labels come first in the Software deck, so a language switch
# is never a trap. Linux names verified in this machine's KDE .desktop files; iOS ones are UNVERIFIED.
ESCAPE = [
    ("System Settings (Linux: way back to English)", "系统设置", "Linux"),
    ("Region & Language (Linux: way back to English)", "区域和语言", "Linux"),
    ("System (Android: way back to English)", "系统", "Android"),
    ("Languages (Android: way back to English)", "语言", "Android"),
    ("General (iOS: way back to English)", "通用", "iOS"),
    ("Language & Region (iOS: way back to English)", "语言与地区", "iOS"),
]
