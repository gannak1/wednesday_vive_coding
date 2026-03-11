class AppError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


class InvalidCategoryError(AppError):
    def __init__(self) -> None:
        super().__init__(400, "INVALID_CATEGORY", "허용되지 않은 카테고리입니다.")


class InvalidContinentError(AppError):
    def __init__(self) -> None:
        super().__init__(400, "INVALID_CONTINENT", "허용되지 않은 대륙입니다.")


class NewsNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(404, "NEWS_NOT_FOUND", "기사를 찾을 수 없습니다.")


class SavedArticleNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(404, "SAVED_ARTICLE_NOT_FOUND", "저장 기사를 찾을 수 없습니다.")


class NewsSourceUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(503, "NEWS_SOURCE_UNAVAILABLE", "뉴스 데이터를 불러올 수 없습니다.")
