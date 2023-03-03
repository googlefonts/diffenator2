import sys
from icu import Locale, BreakIterator

locale = sys.argv[1]
bi = BreakIterator.createWordInstance(Locale(locale))
for line in sys.stdin:
	bi.setText(line)
	start = bi.first()
	for end in bi:
		print(line[start:end])
		start = end
