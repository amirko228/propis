import React, { useState, useEffect } from 'react';
import axios from 'axios';
// Библиотека успешно установлена
import { Document, Page, pdfjs } from 'react-pdf';
import OptionCard from './OptionCard';
import config from '../config';

// Устанавливаем worker для pdf.js
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

// Компонент предпросмотра (может отображать как PDF, так и изображения)
const PreviewViewer = ({ previewUrl, previewType }) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(0.8); // Масштаб по умолчанию 80%
  const [imgScale, setImgScale] = useState(0.8); // Отдельный масштаб для изображений

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  // Увеличение масштаба
  const zoomIn = () => {
    if (scale < 1.5) {
      setScale(scale + 0.1);
    }
  };

  // Уменьшение масштаба
  const zoomOut = () => {
    if (scale > 0.5) {
      setScale(scale - 0.1);
    }
  };

  // Увеличение масштаба для изображения
  const zoomInImage = () => {
    if (imgScale < 1.5) {
      setImgScale(imgScale + 0.1);
    }
  };

  // Уменьшение масштаба для изображения
  const zoomOutImage = () => {
    if (imgScale > 0.5) {
      setImgScale(imgScale - 0.1);
    }
  };

  // Если предпросмотр - это изображение
  if (previewType === 'image') {
    return (
      <div className="preview-viewer">
        <div className="image-container">
          <img 
            src={previewUrl} 
            alt="Предпросмотр прописи"
            style={{ 
              maxWidth: '100%', 
              border: '1px solid #ddd',
              transform: `scale(${imgScale})`,
              transformOrigin: 'top center',
              transition: 'transform 0.2s ease'
            }} 
          />
        </div>
        
        <div className="pdf-controls">
          <button 
            onClick={zoomOutImage} 
            disabled={imgScale <= 0.5}
            title="Уменьшить"
          >
            −
          </button>
          <span title="Масштаб">{Math.round(imgScale * 100)}%</span>
          <button 
            onClick={zoomInImage} 
            disabled={imgScale >= 1.5}
            title="Увеличить"
          >
            +
          </button>
        </div>
      </div>
    );
  }

  // Если предпросмотр - это PDF
  return (
    <div className="preview-viewer">
      <Document
        file={previewUrl}
        onLoadSuccess={onDocumentLoadSuccess}
        error="Ошибка загрузки PDF"
        loading="Загрузка PDF..."
      >
        <Page 
          pageNumber={pageNumber} 
          scale={scale} 
          className="pdf-page"
        />
      </Document>
      <div className="pdf-controls">
        <button 
          disabled={pageNumber <= 1} 
          onClick={() => setPageNumber(pageNumber - 1)}
          title="Предыдущая страница"
        >
          ←
        </button>
        <p>
          Стр. {pageNumber} из {numPages}
        </p>
        <button 
          disabled={pageNumber >= numPages} 
          onClick={() => setPageNumber(pageNumber + 1)}
          title="Следующая страница"
        >
          →
        </button>
        
        <button 
          onClick={zoomOut} 
          disabled={scale <= 0.5}
          title="Уменьшить"
          style={{ marginLeft: '15px' }}
        >
          −
        </button>
        <span title="Масштаб">{Math.round(scale * 100)}%</span>
        <button 
          onClick={zoomIn} 
          disabled={scale >= 1.5}
          title="Увеличить"
        >
          +
        </button>
      </div>
    </div>
  );
};

// Компонент формы для генерации прописей
const PropisiForm = () => {
  // Состояние формы
  const [formData, setFormData] = useState({
    task: 'Обведи буквы по образцу',
    fill_type: 'all', // по умолчанию: заполнить все самостоятельно
    text: 'а а а а а а а а а а а\nб б б б б б б б б б б\nв в в в в в в в в в в',
    page_layout: 'lines', // по умолчанию: линейка
    font_type: 'punktir', // по умолчанию: пунктир
    page_orientation: 'portrait', // по умолчанию: книжная
    student_name: ''
  });
  
  // Состояние загрузки
  const [loading, setLoading] = useState(false);
  // Состояние загрузки предпросмотра
  const [previewLoading, setPreviewLoading] = useState(false);
  // Состояние ошибки
  const [error, setError] = useState(null);
  // Состояние предпросмотра
  const [previewUrl, setPreviewUrl] = useState(null);
  // Тип предпросмотра ('image' или 'pdf')
  const [previewType, setPreviewType] = useState(null);
  // Информационное сообщение
  const [infoMessage, setInfoMessage] = useState(null);
  // Текущий используемый API URL
  const [currentApiUrl, setCurrentApiUrl] = useState(config.API_URL);
  // Индекс текущего API сервера
  const [currentApiIndex, setCurrentApiIndex] = useState(0);
  // Состояние скачивания
  const [downloadStarted, setDownloadStarted] = useState(false);
  // Последний сгенерированный PDF URL
  const [lastPdfUrl, setLastPdfUrl] = useState(null);

  // Функция для переключения на следующий доступный API
  const switchToNextApi = () => {
    const nextIndex = (currentApiIndex + 1) % config.API_URLS.length;
    const nextApiUrl = config.API_URLS[nextIndex];
    setCurrentApiIndex(nextIndex);
    setCurrentApiUrl(nextApiUrl);
    console.log(`Переключаемся на API: ${nextApiUrl}`);
    return nextApiUrl;
  };
  
  // Проверка доступности API при загрузке компонента
  useEffect(() => {
    const checkApi = async () => {
      setInfoMessage('Проверяем доступность серверов...');
      
      // Принудительно устанавливаем первый сервер из списка и считаем его рабочим
      const firstApi = config.API_URLS[0];
      setCurrentApiUrl(firstApi);
      setCurrentApiIndex(0);
      console.log(`Начинаем с API: ${firstApi}`);
      setInfoMessage(null);
      
      // Запускаем асинхронную проверку серверов, но не блокируем интерфейс
      setTimeout(() => {
        testAllServers();
      }, 100);
    };
    
    checkApi();
  }, []);
  
  // Функция асинхронной проверки всех серверов
  const testAllServers = async () => {
    console.log("Начинаем асинхронную проверку всех серверов...");
    
    // Проверяем все серверы параллельно и устанавливаем первый ответивший
    const promises = config.API_URLS.map((url, index) => {
      return testServerWithImage(url, index);
    });
    
    // Запускаем все проверки параллельно
    Promise.all(promises).then(() => {
      console.log("Все проверки серверов завершены");
    }).catch(err => {
      console.error("Ошибка при проверке серверов:", err);
    });
  };
  
  // Проверка сервера с помощью загрузки изображения
  // Этот метод обходит ограничения CORS
  const testServerWithImage = (apiUrl, index) => {
    return new Promise((resolve) => {
      const img = new Image();
      
      // Устанавливаем таймаут на 5 секунд
      const timeout = setTimeout(() => {
        console.log(`Таймаут при проверке ${apiUrl}`);
        resolve(false);
      }, 5000);
      
      // При успешной загрузке изображения
      img.onload = () => {
        clearTimeout(timeout);
        console.log(`Сервер ${apiUrl} доступен (проверка через изображение)`);
        
        // Устанавливаем этот сервер как текущий
        setCurrentApiUrl(apiUrl);
        setCurrentApiIndex(index);
        
        resolve(true);
      };
      
      // При ошибке загрузки
      img.onerror = () => {
        clearTimeout(timeout);
        console.log(`Сервер ${apiUrl} недоступен (проверка через изображение)`);
        resolve(false);
      };
      
      // Запускаем проверку, загружая favicon или другое маленькое изображение с сервера
      // Добавляем случайный параметр для обхода кеширования
      const random = Math.random().toString(36).substring(7);
      img.src = `${apiUrl}/favicon.ico?${random}`;
    });
  };
  
  // Функция проверки доступности API (упрощенная)
  const checkApiAvailability = async (apiUrl = currentApiUrl, timeout = 3000) => {
    try {
      // Всегда возвращаем true, чтобы не блокировать работу приложения
      // Для реальной проверки используем testAllServers
      return true;
    } catch (err) {
      console.error(`API ${apiUrl} недоступен: ${err.message}`);
      return true; // Все равно возвращаем true
    }
  };

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  // Обработчик выбора опции
  const handleOptionSelect = (option, value) => {
    setFormData({
      ...formData,
      [option]: value
    });
  };

  // Функция для загрузки предпросмотра
  const loadPreview = async () => {
    if (previewLoading) return;
    
    setPreviewLoading(true);
    setError(null);
    setInfoMessage('Генерация предпросмотра, пожалуйста подождите...');
    
    // Создаем FormData для отправки на сервер
    const formPayload = new FormData();
    for (const key in formData) {
      formPayload.append(key, formData[key]);
    }
    
    let apiUrl = currentApiUrl;
    let success = false;
    let attempts = 0;
    
    // Пробуем все доступные API
    while (!success && attempts < config.API_URLS.length) {
      try {
        // URL API для предпросмотра
        const requestUrl = `${apiUrl}/preview`;
        console.log('Отправляем запрос превью на:', requestUrl);
        
        // Отправляем запрос на генерацию предпросмотра
        const response = await axios.post(requestUrl, formPayload, {
          responseType: 'blob', // Получаем данные как бинарный файл
          headers: {
            'Accept': 'application/pdf,image/*',
            'Content-Type': 'multipart/form-data'
          },
          timeout: 40000, // Увеличиваем таймаут до 40 секунд
          withCredentials: false
        });
        
        // Проверяем статус ответа
        if (response.status !== 200) {
          throw new Error(`Ошибка сервера: ${response.status}`);
        }
        
        // Определяем тип ответа
        const contentType = response.headers['content-type'];
        console.log('Получен предпросмотр с типом:', contentType);
        
        if (contentType && (contentType.includes('application/pdf') || contentType.includes('image/'))) {
          // Создаем URL объект для отображения
          const blob = new Blob([response.data], { type: contentType });
          const url = URL.createObjectURL(blob);
          
          // Сохраняем URL для предпросмотра
          setPreviewUrl(url);
          setPreviewType(contentType.includes('image') ? 'image' : 'pdf');
          success = true;
          setInfoMessage(null);
        } else {
          // Если содержимое не PDF или изображение, попробуем интерпретировать его как текст ошибки
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const result = reader.result;
              const errorMessage = result.includes('{') 
                ? JSON.parse(result).detail || 'Неизвестная ошибка сервера' 
                : result;
              setError(`Ошибка превью: ${errorMessage}`);
            } catch (e) {
              setError('Произошла неизвестная ошибка при обработке ответа сервера');
            }
          };
          reader.readAsText(response.data);
          
          // Пробуем следующий API
          apiUrl = switchToNextApi();
          attempts++;
        }
      } catch (err) {
        console.error('Ошибка при загрузке предпросмотра:', err);
        
        // Переключаемся на следующий API
        apiUrl = switchToNextApi();
        attempts++;
        
        // Если перепробовали все API, показываем ошибку
        if (attempts >= config.API_URLS.length) {
          if (err.code === 'ECONNABORTED') {
            setError('Превышено время ожидания ответа. Серверы перегружены. Попробуйте упростить текст или повторить позже.');
          } else if (err.response) {
            setError(`Ошибка сервера (${err.response.status}): ${err.response.statusText || 'Попробуйте позже'}`);
          } else if (err.request) {
            setError('Серверы не отвечают. Проверьте подключение к интернету и обновите страницу.');
          } else {
            setError(`Ошибка: ${err.message || 'неизвестная ошибка'}. Попробуйте еще раз.`);
          }
        }
      }
    }
    
    setPreviewLoading(false);
  };

  // Функция для скачивания файла
  const downloadFile = (url, filename = 'propisi.pdf') => {
    try {
      console.log('Инициализация скачивания файла...');
      setDownloadStarted(true);
      
      // Создаем ссылку для скачивания
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      // Добавляем ссылку в DOM
      document.body.appendChild(link);
      
      // Добавляем отслеживание событий
      link.addEventListener('click', () => {
        console.log('Клик по ссылке произошел');
        setTimeout(() => setDownloadStarted(false), 2000);
      });
      
      // Имитация клика
      console.log('Запуск скачивания...');
      link.click();
      
      // Удаление ссылки с задержкой
      setTimeout(() => {
        document.body.removeChild(link);
        console.log('Ссылка скачивания удалена из DOM');
      }, 100);
      
      return true;
    } catch (err) {
      console.error('Ошибка при скачивании файла:', err);
      setError(`Ошибка при скачивании: ${err.message}. Попробуйте еще раз.`);
      setDownloadStarted(false);
      return false;
    }
  };

  // Функция для повторного скачивания
  const retryDownload = () => {
    if (lastPdfUrl) {
      console.log('Повторная попытка скачивания...');
      downloadFile(lastPdfUrl);
    } else {
      setError('Нет доступного файла для скачивания. Пожалуйста, сгенерируйте PDF заново.');
    }
  };

  // Функция для ручной проверки серверов
  const retryServerConnection = async () => {
    setInfoMessage('Проверяем доступность серверов...');
    setError(null);
    
    try {
      // Принудительно проверяем все серверы подряд
      for (let i = 0; i < config.API_URLS.length; i++) {
        const apiUrl = config.API_URLS[i];
        setInfoMessage(`Проверка сервера ${i+1} из ${config.API_URLS.length}: ${apiUrl}`);
        
        try {
          // Прямой запрос без сложной логики
          const response = await fetch(`${apiUrl}/health`, { 
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            credentials: 'omit',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json'
            },
            timeout: 5000
          });
          
          if (response.ok) {
            setCurrentApiUrl(apiUrl);
            setCurrentApiIndex(i);
            setInfoMessage(`Сервер ${apiUrl} доступен и будет использован для запросов`);
            setTimeout(() => setInfoMessage(null), 3000);
            return;
          } else {
            console.log(`Сервер ${apiUrl} ответил с ошибкой ${response.status}`);
          }
        } catch (err) {
          console.error(`Ошибка при проверке ${apiUrl}:`, err.message);
        }
      }
      
      // Если дошли сюда, значит ни один сервер не ответил успешно
      setInfoMessage('Ни один сервер не ответил успешно, но приложение продолжит работать');
      
      // Устанавливаем первый сервер по умолчанию
      setCurrentApiUrl(config.API_URLS[0]);
      setCurrentApiIndex(0);
      
      setTimeout(() => setInfoMessage(null), 3000);
    } catch (err) {
      console.error('Ошибка при проверке серверов:', err);
      setError('Произошла ошибка при проверке серверов');
    }
  };

  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfoMessage('Генерация PDF, пожалуйста подождите...');
    setDownloadStarted(false);
    setLastPdfUrl(null);
    
    // Создаем FormData для отправки на сервер
    const formPayload = new FormData();
    for (const key in formData) {
      formPayload.append(key, formData[key]);
    }
    
    let apiUrl = currentApiUrl;
    let success = false;
    let attempts = 0;
    
    // Пробуем все доступные API
    while (!success && attempts < config.API_URLS.length) {
      try {
        // URL API для генерации PDF
        const requestUrl = `${apiUrl}/generate-pdf`;
        console.log('Отправляем запрос на:', requestUrl);
        
        // Отправляем запрос на генерацию PDF
        const response = await axios.post(requestUrl, formPayload, {
          responseType: 'blob', // Получаем PDF как бинарный файл
          headers: {
            'Accept': 'application/pdf',
            'Content-Type': 'multipart/form-data'
          },
          timeout: 60000, // Таймаут 60 секунд
          withCredentials: false
        });
        
        // Проверяем статус ответа
        if (response.status !== 200) {
          throw new Error(`Ошибка сервера: ${response.status}`);
        }
        
        // Проверяем тип контента
        const contentType = response.headers['content-type'];
        console.log('Получен ответ с типом:', contentType);
        console.log('Размер данных:', response.data.size, 'байт');
        
        // Проверяем, что получили PDF или изображение
        if (contentType && (contentType.includes('application/pdf') || contentType.includes('image/'))) {
          // Создаем URL для скачивания PDF
          const pdfBlob = new Blob([response.data], { type: contentType });
          const url = URL.createObjectURL(pdfBlob);
          
          // Сохраняем URL для предпросмотра и будущего скачивания
          setPreviewUrl(url);
          setPreviewType(contentType.includes('application/pdf') ? 'pdf' : 'image');
          setLastPdfUrl(url);
          
          // Запускаем скачивание
          const downloadSuccess = downloadFile(url);
          
          success = true;
          if (downloadSuccess) {
            setInfoMessage('PDF успешно сгенерирован. Если скачивание не началось автоматически, нажмите "Скачать снова".');
          } else {
            setInfoMessage('PDF успешно сгенерирован, но возникла проблема при скачивании. Нажмите "Скачать снова".');
          }
        } else {
          // Если содержимое не PDF, попробуем интерпретировать его как текст ошибки
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const result = reader.result;
              console.log('Текст ответа:', result);
              const errorMessage = result.includes('{') 
                ? JSON.parse(result).detail || 'Неизвестная ошибка сервера' 
                : result;
              setError(`Ошибка: ${errorMessage}`);
              console.error('Ошибка в ответе сервера:', errorMessage);
            } catch (e) {
              setError('Произошла неизвестная ошибка при обработке ответа сервера');
              console.error('Ошибка при обработке ответа:', e);
            }
          };
          reader.readAsText(response.data);
          
          // Пробуем следующий API
          apiUrl = switchToNextApi();
          attempts++;
        }
      } catch (err) {
        console.error('Ошибка при генерации PDF:', err);
        
        // Переключаемся на следующий API
        apiUrl = switchToNextApi();
        attempts++;
        
        // Если перепробовали все API, показываем ошибку
        if (attempts >= config.API_URLS.length) {
          if (err.code === 'ECONNABORTED') {
            setError('Превышено время ожидания ответа. Серверы перегружены. Попробуйте упростить текст или повторить позже.');
          } else if (err.response) {
            setError(`Ошибка сервера (${err.response.status}): ${err.response.statusText || 'Попробуйте позже'}`);
          } else if (err.request) {
            setError('Проблема подключения к серверам. Проверьте интернет и обновите страницу.');
          } else {
            setError(`Ошибка: ${err.message || 'неизвестная ошибка'}. Попробуйте позже.`);
          }
        }
      }
    }
    
    setLoading(false);
  };

  return (
    <div className="form-container">
      <h2 className="form-title">Онлайн-генератор прописей для детей</h2>
      
      <div className="form-description">
        <p>Создавайте красивые прописи для обучения детей письму. Выберите варианты оформления и введите нужный текст.</p>
      </div>
      
      {/* Информация о текущем сервере */}
      {currentApiUrl && (
        <div className="current-server">
          Используемый сервер: <strong>{currentApiUrl}</strong>
          <button 
            onClick={retryServerConnection}
            className="server-refresh"
            title="Проверить серверы"
          >
            ↻
          </button>
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        {/* Секция разметки страницы */}
        <div className="form-group">
          <label className="section-label">Выберите вид фоновой разметки:</label>
          <div className="options-container">
            <OptionCard
              title="Клетка"
              img="/images/cells.svg"
              selected={formData.page_layout === 'cells'}
              onClick={() => handleOptionSelect('page_layout', 'cells')}
            />
            <OptionCard
              title="Линейка"
              img="/images/lines.svg"
              selected={formData.page_layout === 'lines'}
              onClick={() => handleOptionSelect('page_layout', 'lines')}
            />
            <OptionCard
              title="Косая линейка"
              img="/images/lines_oblique.svg"
              selected={formData.page_layout === 'lines_oblique'}
              onClick={() => handleOptionSelect('page_layout', 'lines_oblique')}
            />
          </div>
        </div>

        {/* Секция шрифта */}
        <div className="form-group">
          <label className="section-label">Задайте тип и цвет линии:</label>
          <div className="options-container">
            <OptionCard
              title="Пунктир"
              img="/images/punktir.svg"
              selected={formData.font_type === 'punktir'}
              onClick={() => handleOptionSelect('font_type', 'punktir')}
            />
            <OptionCard
              title="Серый"
              img="/images/gray.svg"
              selected={formData.font_type === 'gray'}
              onClick={() => handleOptionSelect('font_type', 'gray')}
            />
            <OptionCard
              title="Черный"
              img="/images/black.svg"
              selected={formData.font_type === 'black'}
              onClick={() => handleOptionSelect('font_type', 'black')}
            />
          </div>
        </div>

        {/* Секция ориентации страницы */}
        <div className="form-group">
          <label className="section-label">Выберите ориентацию страницы:</label>
          <div className="options-container">
            <OptionCard
              title="Книжная"
              img="/images/portrait.svg"
              selected={formData.page_orientation === 'portrait'}
              onClick={() => handleOptionSelect('page_orientation', 'portrait')}
            />
            <OptionCard
              title="Альбомная"
              img="/images/landscape.svg"
              selected={formData.page_orientation === 'landscape'}
              onClick={() => handleOptionSelect('page_orientation', 'landscape')}
            />
          </div>
        </div>

        {/* Секция имени ученика */}
        <div className="form-group">
          <label htmlFor="student_name" className="section-label">Имя ученика (до 25 символов):</label>
          <input
            type="text"
            id="student_name"
            name="student_name"
            className="form-control"
            value={formData.student_name}
            onChange={handleChange}
            placeholder="Например, Миша"
            maxLength={25}
          />
        </div>

        {/* Секция задания */}
        <div className="form-group">
          <label htmlFor="task" className="section-label">Задание (до 80 символов):</label>
          <input
            type="text"
            id="task"
            name="task"
            className="form-control"
            value={formData.task}
            onChange={handleChange}
            maxLength={80}
            placeholder="Например, обведи буквы по примеру"
            required
          />
        </div>

        {/* Секция варианта заполнения */}
        <div className="form-group">
          <label className="section-label">Вариант заполнения:</label>
          <div className="radio-group">
            <label className="radio-option">
              <input
                type="radio"
                name="fill_type"
                value="all"
                checked={formData.fill_type === 'all'}
                onChange={handleChange}
              />
              Заполнить все самостоятельно
            </label>
            <label className="radio-option">
              <input
                type="radio"
                name="fill_type"
                value="first_letter"
                checked={formData.fill_type === 'first_letter'}
                onChange={handleChange}
              />
              Размножить первую букву в каждой строке
            </label>
            <label className="radio-option">
              <input
                type="radio"
                name="fill_type"
                value="one_line"
                checked={formData.fill_type === 'one_line'}
                onChange={handleChange}
              />
              Размножить одну строку на всю страницу
            </label>
          </div>
        </div>

        {/* Секция текста прописи */}
        <div className="form-group">
          <label htmlFor="text" className="section-label">Текст прописи:</label>
          <textarea
            id="text"
            name="text"
            className="form-control text-area"
            value={formData.text}
            onChange={handleChange}
            placeholder="Введите буквы, слоги, слова или любой другой текст"
            required
          />
          <div className="form-hint">Пустые строки останутся пустыми на странице, а длинные перенесутся автоматически</div>
        </div>

        {/* Сообщение об ошибке */}
        {error && (
          <div className="error-message">
            {error}
            {error.includes('недоступны') && (
              <button 
                type="button" 
                className="button button-small" 
                onClick={retryServerConnection}
                style={{marginLeft: '10px', padding: '5px 10px', fontSize: '0.9rem'}}
              >
                Проверить снова
              </button>
            )}
          </div>
        )}

        {/* Информационное сообщение */}
        {infoMessage && (
          <div className={`info-message ${error ? 'info-hidden' : ''}`}>
            {infoMessage}
            {(loading || previewLoading) && (
              <span className="loading-dots">
                <span className="dot">.</span>
                <span className="dot">.</span>
                <span className="dot">.</span>
              </span>
            )}
          </div>
        )}
        
        {/* Кнопки управления */}
        <div className="button-group">
          {/* Кнопка предпросмотра */}
          <button 
            type="button" 
            className="button button-secondary" 
            onClick={loadPreview} 
            disabled={previewLoading || loading}
          >
            {previewLoading ? 'Загрузка...' : 'Предпросмотр'}
          </button>
          
          {/* Кнопка отправки */}
          <button 
            type="submit" 
            className="button" 
            disabled={loading || previewLoading}
          >
            {loading ? 'Генерация...' : 'Сгенерировать пропись'}
          </button>
          
          {/* Кнопка повторного скачивания */}
          {lastPdfUrl && (
            <button 
              type="button"
              className="button button-secondary"
              onClick={retryDownload}
              disabled={loading || previewLoading}
            >
              Скачать снова
            </button>
          )}
        </div>

        {/* Предпросмотр */}
        {previewUrl && (
          <div className="preview-container">
            <h3>Предпросмотр:</h3>
            <PreviewViewer previewUrl={previewUrl} previewType={previewType} />
          </div>
        )}
      </form>
    </div>
  );
};

export default PropisiForm; 