import React, { useState, useEffect } from 'react';
import axios from 'axios';
// Библиотека успешно установлена
import { Document, Page, pdfjs } from 'react-pdf';
import OptionCard from './OptionCard';
import config from '../config';

// Устанавливаем worker для pdf.js - исправленная конфигурация
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

// Проверка доступности worker'а
try {
  if (typeof window !== 'undefined') {
    const workerBlob = new Blob(
      [`importScripts('https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js');`],
      { type: 'application/javascript' }
    );
    pdfjs.GlobalWorkerOptions.workerSrc = URL.createObjectURL(workerBlob);
  }
} catch (e) {
  console.error('Ошибка при инициализации PDF worker:', e);
}

// Создаем axios-клиент с настройками для проверки
const checkAxios = axios.create({
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'X-Requested-With': 'XMLHttpRequest'
  }
});

// Функция для проверки доступности сервера
const checkServerAvailability = async (url) => {
  try {
    // Проверяем доступность с помощью простого GET-запроса
    const response = await checkAxios.get(`${url}/health`, { timeout: 5000 });
    return response.status === 200;
  } catch (error) {
    console.log(`Сервер ${url} недоступен:`, error.message);
    return false;
  }
};

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
        error={
          <div className="pdf-error">
            <p>Ошибка загрузки PDF.</p>
            <button onClick={() => window.open(previewUrl, '_blank')}>
              Открыть PDF в новой вкладке
            </button>
          </div>
        }
        loading={
          <div className="pdf-loading">
            <p>Загрузка PDF...</p>
            <div className="loading-spinner"></div>
          </div>
        }
        noData={
          <div className="pdf-no-data">
            <p>PDF не содержит данных или повреждён.</p>
          </div>
        }
      >
        <Page 
          pageNumber={pageNumber} 
          scale={scale} 
          className="pdf-page"
          error={
            <div className="pdf-page-error">
              <p>Ошибка при отображении страницы.</p>
            </div>
          }
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
  // Состояние для отображения резервной опции
  const [showFallbackOption, setShowFallbackOption] = useState(false);

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
  const retryServerConnection = () => {
    setInfoMessage('Переключаемся на следующий сервер...');
    switchToNextApi();
    setTimeout(() => setInfoMessage(null), 2000);
  };

  // Функция для резервной генерации PDF на клиенте
  const generateFallbackPDF = async () => {
    setLoading(true);
    setError(null);
    setInfoMessage('Генерация PDF локально в браузере, пожалуйста подождите...');
    
    try {
      console.log('Начало генерации PDF...');
      
      try {
        // Сначала проверим наличие jsPDF
        if (typeof window === 'undefined') {
          throw new Error('Window объект недоступен');
        }
        
        // Динамический импорт библиотеки jsPDF
        const jsPDFModule = await import('jspdf');
        console.log('jsPDF модуль загружен:', jsPDFModule);
        
        // Простейшая генерация PDF с минимумом функций
        const { jsPDF } = jsPDFModule.default;
        console.log('jsPDF конструктор доступен:', typeof jsPDF);
        
        // Создаем документ с минимальными настройками
        const pdf = new jsPDF({
          orientation: 'portrait',
          unit: 'mm',
          format: 'a4'
        });
        
        console.log('PDF объект создан успешно');
        
        // Добавляем простой текст без сложного форматирования
        pdf.setFont('helvetica');
        pdf.setFontSize(16);
        pdf.text('ПРОСТАЯ ПРОПИСЬ', 105, 20, { align: 'center' });
        
        // Добавляем текст из формы
        pdf.setFontSize(14);
        pdf.text('Текст:', 20, 40);
        
        // Разбиваем на строки и добавляем их по одной
        const lines = formData.text.split('\n');
        let y = 50;
        for (let i = 0; i < Math.min(lines.length, 20); i++) {
          pdf.text(lines[i], 20, y);
          y += 10;
        }
        
        // Сохраняем PDF
        console.log('Сохраняем PDF...');
        const pdfUrl = pdf.output('datauristring');
        console.log('PDF URL создан');
        
        // Показываем превью
        setPreviewUrl(pdfUrl);
        setPreviewType('pdf');
        setLastPdfUrl(pdfUrl);
        
        // Скачиваем без сложного кода
        try {
          const link = document.createElement('a');
          link.href = pdfUrl;
          link.setAttribute('download', 'propisi.pdf');
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          
          setInfoMessage('PDF успешно сгенерирован в браузере.');
        } catch (dlError) {
          console.error('Ошибка при скачивании PDF:', dlError);
          setInfoMessage('PDF сгенерирован, но не удалось запустить скачивание автоматически. Пожалуйста, нажмите "Скачать снова".');
        }
      } catch (pdfError) {
        console.error('Ошибка при работе с jsPDF:', pdfError);
        // Пробуем запасной вариант
        throw pdfError;
      }
    } catch (error) {
      console.error('Детальная ошибка при генерации PDF:', error);
      
      // Пробуем через другой API
      try {
        console.log('Пробуем альтернативный метод генерации PDF...');
        
        // Создаем HTML с текстом для печати
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
          throw new Error('Не удалось открыть окно печати. Проверьте настройки блокировщика всплывающих окон.');
        }
        
        printWindow.document.write(`
          <!DOCTYPE html>
          <html>
          <head>
            <title>Пропись</title>
            <style>
              body {
                font-family: Arial, sans-serif;
                padding: 20px;
              }
              h1 {
                text-align: center;
                margin-bottom: 20px;
              }
              .task {
                margin-bottom: 20px;
              }
              .content {
                white-space: pre-wrap;
                line-height: 2;
                font-size: 16px;
              }
              .print-button {
                display: block;
                margin: 20px auto;
                padding: 10px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
              }
            </style>
          </head>
          <body>
            <h1>ПРОПИСЬ</h1>
            <div class="task">Задание: ${formData.task}</div>
            ${formData.student_name ? `<div class="task">Ученик: ${formData.student_name}</div>` : ''}
            <div class="content">${formData.text}</div>
            <button class="print-button" onclick="window.print(); return false;">Распечатать</button>
          </body>
          </html>
        `);
        
        printWindow.document.close();
        
        setInfoMessage('Открыт документ для печати. Используйте браузерную печать для сохранения в PDF.');
        setError(null);
      } catch (alternativeError) {
        console.error('Ошибка при альтернативной генерации:', alternativeError);
        setError(`Не удалось создать PDF в браузере: ${error.message || 'неизвестная ошибка'}. Попробуйте другой браузер.`);
      }
    } finally {
      setLoading(false);
    }
  };

  // Загрузка предпросмотра локально
  const loadPreview = async () => {
    if (previewLoading) return;
    
    setPreviewLoading(true);
    setError(null);
    setInfoMessage('Генерация предпросмотра, пожалуйста подождите...');
    
    try {
      // Динамический импорт библиотеки jsPDF только когда она нужна
      const jsPDFModule = await import('jspdf');
      const { jsPDF } = jsPDFModule.default;
      
      // Создаем новый PDF документ
      const orientation = formData.page_orientation === 'landscape' ? 'landscape' : 'portrait';
      const pdf = new jsPDF({
        orientation: orientation,
        unit: 'mm',
        format: 'a4'
      });
      
      // Добавляем базовую информацию
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(16);
      pdf.text('ПРОПИСЬ (предпросмотр)', 105, 20, { align: 'center' });
      
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(12);
      pdf.text(`Задание: ${formData.task}`, 20, 30);
      
      if (formData.student_name) {
        pdf.text(`Ученик: ${formData.student_name}`, 20, 40);
      }
      
      // Определяем параметры в зависимости от типа разметки
      let lineHeight = 10;
      let startY = 50;
      let xMargin = 20;
      
      // Добавляем фоновую разметку
      if (formData.page_layout === 'lines') {
        // Рисуем линии
        let y = startY;
        while (y < 270) {
          pdf.setDrawColor(200, 200, 200);
          pdf.line(xMargin, y, 190, y);
          y += lineHeight;
        }
      } else if (formData.page_layout === 'cells') {
        // Рисуем клетки
        let y = startY;
        while (y < 270) {
          pdf.setDrawColor(200, 200, 200);
          for (let x = xMargin; x < 190; x += 10) {
            pdf.line(x, startY, x, 270);  // Вертикальные линии
          }
          pdf.line(xMargin, y, 190, y);  // Горизонтальные линии
          y += 10;
        }
      } else if (formData.page_layout === 'lines_oblique') {
        // Рисуем косые линейки
        let y = startY;
        while (y < 270) {
          pdf.setDrawColor(200, 200, 200);
          pdf.line(xMargin, y, 190, y); // Обычная линия
          
          // Добавляем наклонные линии
          if (y + lineHeight < 270) {
            pdf.setDrawColor(220, 220, 220);
            for (let x = xMargin; x < 190; x += 15) {
              pdf.line(x, y, x + 10, y + lineHeight);
            }
          }
          
          y += lineHeight;
        }
      }
      
      // Тип шрифта для текста
      let textColor = [0, 0, 0]; // Черный по умолчанию
      if (formData.font_type === 'gray') {
        textColor = [150, 150, 150]; // Серый
      } else if (formData.font_type === 'punktir') {
        // Для пунктира используем черный, но специальную функцию рисования
        textColor = [0, 0, 0];
      }
      
      // Добавляем текст прописи
      pdf.setFontSize(16);
      pdf.setTextColor(textColor[0], textColor[1], textColor[2]);
      
      const lines = formData.text.split('\n');
      let yPos = startY + 8; // Отступ для текста
      
      // Обработка разных типов заполнения
      if (formData.fill_type === 'one_line' && lines.length > 0) {
        // Размножаем первую строку на весь документ
        const firstLine = lines[0];
        while (yPos < 260) {
          pdf.text(firstLine, xMargin + 5, yPos);
          yPos += lineHeight;
        }
      } else if (formData.fill_type === 'first_letter') {
        // Размножаем первую букву каждой строки
        lines.forEach(line => {
          if (line.trim()) {
            const firstLetter = line.trim()[0];
            let repeatedLetters = '';
            for (let i = 0; i < 20; i++) {
              repeatedLetters += firstLetter + ' ';
            }
            pdf.text(repeatedLetters, xMargin + 5, yPos);
            yPos += lineHeight;
          } else {
            yPos += lineHeight; // Пустая строка
          }
        });
      } else {
        // Обычное заполнение - используем текст как есть
        lines.forEach(line => {
          if (line.trim()) {
            pdf.text(line, xMargin + 5, yPos);
            yPos += lineHeight;
          } else {
            yPos += lineHeight; // Пустая строка
          }
        });
      }
      
      // Добавляем дату и время
      const now = new Date();
      const dateStr = now.toLocaleDateString('ru-RU');
      pdf.setFontSize(10);
      pdf.setTextColor(100, 100, 100);
      pdf.text(`Предпросмотр: ${dateStr}`, 20, 280);
      
      // Сохраняем PDF
      const pdfUrl = pdf.output('datauristring');
      
      // Показываем превью, но НЕ скачиваем
      setPreviewUrl(pdfUrl);
      setPreviewType('pdf');
      setInfoMessage(null);
    } catch (error) {
      console.error('Ошибка при генерации предпросмотра:', error);
      setError('Не удалось создать предпросмотр. Попробуйте генерацию PDF напрямую.');
    }
    
    setPreviewLoading(false);
  };

  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Используем локальную генерацию как основную
    await generateFallbackPDF();
  };

  // Серверная генерация PDF как запасной вариант
  const generateServerPDF = async () => {
    setLoading(true);
    setError(null);
    setInfoMessage('Генерация PDF на сервере, пожалуйста подождите...');
    setDownloadStarted(false);
    setLastPdfUrl(null);
    
    // Создаем FormData для отправки на сервер
    const formPayload = new FormData();
    for (const key in formData) {
      formPayload.append(key, formData[key]);
    }
    
    let success = false;
    let errorMessages = [];
    
    // Создаем axios-клиент с CORS-прокси
    const axiosClient = axios.create({
      responseType: 'blob',
      headers: {
        'Accept': 'application/pdf,image/*',
        'Content-Type': 'multipart/form-data',
        'Access-Control-Allow-Origin': '*',
        'X-Requested-With': 'XMLHttpRequest'
      },
      timeout: 90000,
      withCredentials: false
    });
    
    // Пробуем все серверы по очереди
    for (let i = 0; i < config.API_URLS.length; i++) {
      const apiUrl = config.API_URLS[i];
      setCurrentApiUrl(apiUrl);
      setCurrentApiIndex(i);
      
      try {
        console.log(`Пробуем сервер для генерации PDF: ${apiUrl}`);
        const requestUrl = `${apiUrl}/generate-pdf`;
        
        // Добавляем случайное число для обхода кэша
        const randomParam = `?_=${Date.now()}`;
        
        // Отправляем запрос
        const response = await axiosClient.post(requestUrl + randomParam, formPayload);
        
        if (response.status === 200) {
          const contentType = response.headers['content-type'];
          
          if (contentType && (contentType.includes('application/pdf') || contentType.includes('image/'))) {
            const blob = new Blob([response.data], { type: contentType });
            const url = URL.createObjectURL(blob);
            
            setPreviewUrl(url);
            setPreviewType(contentType.includes('application/pdf') ? 'pdf' : 'image');
            setLastPdfUrl(url);
            
            // Скачиваем автоматически
            try {
              const link = document.createElement('a');
              link.href = url;
              link.setAttribute('download', 'propisi.pdf');
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              
              setInfoMessage('PDF успешно сгенерирован на сервере. Если скачивание не началось автоматически, нажмите "Скачать снова".');
            } catch (dlError) {
              console.error('Ошибка при скачивании PDF:', dlError);
              setInfoMessage('PDF сгенерирован, но не удалось запустить скачивание автоматически. Нажмите "Скачать снова".');
            }
            
            success = true;
            break;
          } else {
            errorMessages.push(`Сервер ${apiUrl} вернул некорректный формат: ${contentType}`);
          }
        } else {
          errorMessages.push(`Сервер ${apiUrl} вернул статус ${response.status}`);
        }
      } catch (err) {
        console.error(`Ошибка на сервере ${apiUrl}:`, err.message);
        if (err.response) {
          console.error('Данные ответа:', err.response.data);
          console.error('Статус:', err.response.status);
          console.error('Заголовки:', err.response.headers);
        }
        errorMessages.push(`${apiUrl}: ${err.message}`);
      }
    }
    
    if (!success) {
      setError(`Не удалось сгенерировать PDF на сервере. Попробуйте локальный метод. Детали: ${errorMessages.length > 0 ? errorMessages[0] : 'серверы недоступны'}`);
    }
    
    setLoading(false);
  };

  return (
    <div className="form-container">
      <h2 className="form-title">Онлайн-генератор прописей для детей</h2>
      
      <div className="form-description">
        <p>Создавайте красивые прописи для обучения детей письму. Выберите варианты оформления и введите нужный текст.</p>
      </div>
      
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
          
          {/* Кнопка основной генерации */}
          <button 
            type="submit" 
            className="button" 
            disabled={loading || previewLoading}
          >
            {loading ? 'Генерация...' : 'Сгенерировать в браузере'}
          </button>
          
          {/* Кнопка серверной генерации */}
          <button
            type="button"
            className="button button-server"
            onClick={generateServerPDF}
            disabled={loading || previewLoading}
          >
            Сгенерировать на сервере
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