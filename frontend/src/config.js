// Конфигурация приложения
const config = {
  // URL API бэкенда
  API_URL: process.env.REACT_APP_API_URL || 'https://propisi-backend.vercel.app',
  
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

export default config; 