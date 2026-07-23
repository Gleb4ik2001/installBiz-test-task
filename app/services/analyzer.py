class Service:
    def __init__(self):
        pass

    @staticmethod
    def analyze_digits(content: str) -> dict:
        """Подсчитывает количество каждой цифры (0-9) в тексте."""
        stats = {str(i): 0 for i in range(10)}
        for char in content.strip():
            if char in stats:
                stats[char] += 1
        return stats
