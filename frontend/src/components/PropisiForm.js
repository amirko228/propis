import React, { useState } from 'react';
import axios from 'axios';
// Библиотека успешно установлена
import { Document, Page, pdfjs } from 'react-pdf';
import OptionCard from './OptionCard';

// Устанавливаем worker для pdf.js
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.js`;

// API URL, проверяем среду выполнения
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
  // Состояния формы
  const [formData, setFormData] = useState({
    task: "Прописи",
    fill_type: "all",
    text: "Пример текста для прописи",
    page_layout: "lines",
    font_type: "black",
    page_orientation: "portrait",
    student_name: "",
  });

  // Состояние для предпросмотра
  const [previewUrl, setPreviewUrl] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Обработчик отправки формы и генерации PDF
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    
    try {
      // Формируем данные формы
      const form = new FormData();
      Object.keys(formData).forEach(key => {
        form.append(key, formData[key]);
      });
      
      console.log("Отправляем запрос на генерацию PDF:", formData);
      
      // Отправляем запрос на сервер
      const response = await axios({
        method: 'post',
        url: `${API_URL}/api/generate-pdf`,
        data: form,
        responseType: 'blob', // Важно для получения бинарных данных
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      console.log("Ответ получен:", response);
      
      // Создаем URL для скачивания PDF
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'propisi.pdf');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setIsLoading(false);
    } catch (err) {
      console.error("Ошибка при генерации PDF:", err);
      setError("Произошла ошибка при генерации PDF. Пожалуйста, попробуйте еще раз.");
      setIsLoading(false);
    }
  };

  // Функция для генерации предпросмотра
  const handlePreview = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Формируем данные формы для предпросмотра
      const form = new FormData();
      Object.keys(formData).forEach(key => {
        form.append(key, formData[key]);
      });
      
      console.log("Отправляем запрос на предпросмотр:", formData);
      
      // Отправляем запрос на сервер - отдельный endpoint для предпросмотра
      const response = await axios({
        method: 'post',
        url: `${API_URL}/api/preview`,
        data: form,
        responseType: 'blob', // Важно для получения бинарных данных
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      console.log("Ответ на предпросмотр получен:", response);
      
      // Создаем URL для отображения PDF в предпросмотре
      const pdfBlob = new Blob([response.data], { type: 'application/pdf' });
      const pdfUrl = URL.createObjectURL(pdfBlob);
      setPreviewUrl(pdfUrl);
      setIsLoading(false);
    } catch (err) {
      console.error("Ошибка при генерации предпросмотра:", err);
      setError("Произошла ошибка при генерации предпросмотра. Пожалуйста, попробуйте еще раз.");
      setIsLoading(false);
    }
  };

  // Обработчик загрузки PDF для предпросмотра
  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  // Опции для формы выбора
  const taskOptions = ["Прописи", "Каллиграфия", "Чистописание", "Упражнения"];
  const fillTypeOptions = [
    { value: "all", label: "Весь текст" },
    { value: "first_letter", label: "Только первые буквы" },
    { value: "one_line", label: "Повторение первой строки" },
  ];
  const pageLayoutOptions = [
    { value: "lines", label: "Линейки" },
    { value: "lines_oblique", label: "Линейки с наклоном" },
    { value: "cells", label: "Клетки" },
  ];
  const fontTypeOptions = [
    { value: "black", label: "Черный" },
    { value: "gray", label: "Серый" },
    { value: "punktir", label: "Пунктирный" },
  ];
  const pageOrientationOptions = [
    { value: "portrait", label: "Портрет" },
    { value: "landscape", label: "Альбом" },
  ];

  return (
    <div className="propisi-form-container">
      <h2>Генератор прописей</h2>
      <div className="form-preview-wrapper">
        <div className="form-section">
          <form onSubmit={handleSubmit}>
            {/* Тип задания */}
            <div className="form-field">
              <label htmlFor="task">Тип задания:</label>
              <select
                id="task"
                name="task"
                value={formData.task}
                onChange={handleChange}
              >
                {taskOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>

            {/* Текст прописи */}
            <div className="form-field">
              <label htmlFor="text">Текст прописи:</label>
              <textarea
                id="text"
                name="text"
                value={formData.text}
                onChange={handleChange}
                rows={6}
                placeholder="Введите текст для прописи..."
                required
              />
              <p className="form-help-text">
                Пустые строки останутся пустыми на странице, а длинные перенесутся автоматически
              </p>
            </div>

            {/* Имя ученика */}
            <div className="form-field">
              <label htmlFor="student_name">Имя ученика (необязательно):</label>
              <input
                type="text"
                id="student_name"
                name="student_name"
                value={formData.student_name}
                onChange={handleChange}
                placeholder="Например: Иванов Иван"
              />
            </div>

            {/* Опции генерации */}
            <div className="form-options">
              <h3>Опции генерации</h3>
              <div className="options-grid">
                {/* Тип заполнения */}
                <div className="option-group">
                  <p className="option-title">Тип заполнения:</p>
                  <div className="option-cards">
                    {fillTypeOptions.map((option) => (
                      <OptionCard
                        key={option.value}
                        option={option}
                        name="fill_type"
                        selectedValue={formData.fill_type}
                        onChange={handleChange}
                      />
                    ))}
                  </div>
                </div>

                {/* Тип разметки */}
                <div className="option-group">
                  <p className="option-title">Тип разметки:</p>
                  <div className="option-cards">
                    {pageLayoutOptions.map((option) => (
                      <OptionCard
                        key={option.value}
                        option={option}
                        name="page_layout"
                        selectedValue={formData.page_layout}
                        onChange={handleChange}
                      />
                    ))}
                  </div>
                </div>

                {/* Тип шрифта */}
                <div className="option-group">
                  <p className="option-title">Тип шрифта:</p>
                  <div className="option-cards">
                    {fontTypeOptions.map((option) => (
                      <OptionCard
                        key={option.value}
                        option={option}
                        name="font_type"
                        selectedValue={formData.font_type}
                        onChange={handleChange}
                      />
                    ))}
                  </div>
                </div>

                {/* Ориентация страницы */}
                <div className="option-group">
                  <p className="option-title">Ориентация:</p>
                  <div className="option-cards">
                    {pageOrientationOptions.map((option) => (
                      <OptionCard
                        key={option.value}
                        option={option}
                        name="page_orientation"
                        selectedValue={formData.page_orientation}
                        onChange={handleChange}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Кнопки действий */}
            <div className="form-actions">
              <button
                type="button"
                className="preview-button"
                onClick={handlePreview}
                disabled={isLoading}
              >
                Предпросмотр
              </button>
              <button
                type="submit"
                className="generate-button"
                disabled={isLoading}
              >
                Сгенерировать пропись
              </button>
            </div>

            {/* Сообщение об ошибке */}
            {error && <div className="error-message">{error}</div>}
            {isLoading && <div className="loading-message">Подождите, идет генерация...</div>}
          </form>
        </div>

        {/* Секция предпросмотра */}
        <div className="preview-section">
          <h3>Предпросмотр</h3>
          {previewUrl ? (
            <div className="pdf-preview">
              <Document
                file={previewUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                className="pdf-document"
              >
                <Page pageNumber={1} width={300} className="pdf-page" />
              </Document>
              <p className="preview-info">
                Страница 1 {numPages && `из ${numPages}`}
              </p>
            </div>
          ) : (
            <div className="preview-placeholder">
              <p>Здесь будет отображен предпросмотр генерируемого PDF-файла</p>
              <p>Нажмите кнопку "Предпросмотр" для генерации</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PropisiForm; 