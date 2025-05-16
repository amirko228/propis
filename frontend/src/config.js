// Конфигурация приложения
const config = {
  // URL API бэкенда - массив резервных серверов
  API_URLS: [
    'http://localhost:8000',
    'https://propisi-backend.onrender.com',
    'https://propisi-api.adaptable.app',
    'https://propisi-api-2.onrender.com'
  ],
  
  // URL API для использования по умолчанию
  API_URL: process.env.NODE_ENV === 'development' 
    ? 'http://localhost:8000' 
    : 'https://propisi-backend.onrender.com',
  
  // Названия вариантов заполнения
  FILL_TYPES: {
    all: 'Заполнить все самостоятельно',
    first_letter: 'Размножить первую букву в каждой строке',
    one_line: 'Размножить одну строку на всю страницу'
  },
  
  // Названия разметок страницы
  PAGE_LAYOUTS: {
    cells: 'Клетка',
    lines: 'Линейка',
    lines_oblique: 'Косая линейка'
  },
  
  // Названия видов линий
  FONT_TYPES: {
    punktir: 'Пунктир',
    gray: 'Серый',
    black: 'Черный'
  },
  
  // Названия ориентаций страницы
  PAGE_ORIENTATIONS: {
    portrait: 'Книжная',
    landscape: 'Альбомная'
  }
};

// Логгирование используемого API URL для отладки
console.log('Используется API URL:', config.API_URL);

export default config; 