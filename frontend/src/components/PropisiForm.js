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
    // Всегда начинаем с первого сервера без проверок
    const firstApi = config.API_URLS[0];
    setCurrentApiUrl(firstApi);
    setCurrentApiIndex(0);
    console.log(`Используем сервер по умолчанию: ${firstApi}`);
    setInfoMessage(null);
  }, []);
  
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
    
    let success = false;
    
    // Пробуем все серверы по очереди
    for (let i = 0; i < config.API_URLS.length; i++) {
      const apiUrl = config.API_URLS[i];
      setCurrentApiUrl(apiUrl);
      setCurrentApiIndex(i);
      
      try {
        console.log(`Пробуем сервер для превью: ${apiUrl}`);
        const requestUrl = `${apiUrl}/preview`;
        
        // Отправляем запрос с увеличенным таймаутом
        const response = await axios.post(requestUrl, formPayload, {
          responseType: 'blob',
          headers: {
            'Accept': 'application/pdf,image/*',
            'Content-Type': 'multipart/form-data'
          },
          timeout: 45000,
          withCredentials: false
        });
        
        if (response.status === 200) {
          const contentType = response.headers['content-type'];
          
          if (contentType && (contentType.includes('application/pdf') || contentType.includes('image/'))) {
            const blob = new Blob([response.data], { type: contentType });
            const url = URL.createObjectURL(blob);
            
            setPreviewUrl(url);
            setPreviewType(contentType.includes('image') ? 'image' : 'pdf');
            setInfoMessage(null);
            success = true;
            break;
          }
        }
      } catch (err) {
        console.error(`Ошибка на сервере ${apiUrl}:`, err.message);
        // Продолжаем со следующим сервером
      }
    }
    
    if (!success) {
      setError('Не удалось создать предпросмотр. Попробуйте снова или используйте кнопку "Сгенерировать пропись".');
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
    setInfoMessage('Переключаемся на следующий сервер...');
    switchToNextApi();
    setTimeout(() => setInfoMessage(null), 2000);
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
    
    let success = false;
    
    // Пробуем все серверы по очереди
    for (let i = 0; i < config.API_URLS.length; i++) {
      const apiUrl = config.API_URLS[i];
      setCurrentApiUrl(apiUrl);
      setCurrentApiIndex(i);
      
      try {
        console.log(`Пробуем сервер для генерации PDF: ${apiUrl}`);
        const requestUrl = `${apiUrl}/generate-pdf`;
        
        // Отправляем запрос с увеличенным таймаутом
        const response = await axios.post(requestUrl, formPayload, {
          responseType: 'blob',
          headers: {
            'Accept': 'application/pdf,image/*',
            'Content-Type': 'multipart/form-data'
          },
          timeout: 60000,
          withCredentials: false
        });
        
        if (response.status === 200) {
          const contentType = response.headers['content-type'];
          
          if (contentType && (contentType.includes('application/pdf') || contentType.includes('image/'))) {
            const blob = new Blob([response.data], { type: contentType });
            const url = URL.createObjectURL(blob);
            
            setPreviewUrl(url);
            setPreviewType(contentType.includes('application/pdf') ? 'pdf' : 'image');
            setLastPdfUrl(url);
            
            const downloadSuccess = downloadFile(url);
            
            success = true;
            if (downloadSuccess) {
              setInfoMessage('PDF успешно сгенерирован. Если скачивание не началось автоматически, нажмите "Скачать снова".');
            } else {
              setInfoMessage('PDF успешно сгенерирован, но возникла проблема при скачивании. Нажмите "Скачать снова".');
            }
            break;
          }
        }
      } catch (err) {
        console.error(`Ошибка на сервере ${apiUrl}:`, err.message);
        // Продолжаем со следующим сервером
      }
    }
    
    if (!success) {
      setError('Не удалось сгенерировать PDF. Попробуйте упростить задание или повторите позже.');
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