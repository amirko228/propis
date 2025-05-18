import React, { useState } from 'react';
import axios from 'axios';
// Удаляем неиспользуемые импорты
import OptionCard from './OptionCard';

// Компонент предпросмотра (теперь будет просто отображать текстовое сообщение)
const PreviewViewer = ({ message }) => {
  if (!message) return null;
  
  return (
    <div className="preview-message">
      <div style={{ 
        padding: '20px', 
        backgroundColor: '#f9f9f9', 
        border: '1px solid #ddd',
        borderRadius: '5px',
        margin: '10px 0'
      }}>
        <h3>Результат обработки:</h3>
        <p>{message}</p>
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
  // Сообщение о результате операции
  const [resultMessage, setResultMessage] = useState(null);
  // Флаг успешной операции
  const [success, setSuccess] = useState(false);

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
    
    // Сбрасываем сообщения об ошибках при изменении формы
    setError(null);
  };

  // Обработчик выбора опции
  const handleOptionSelect = (option, value) => {
    setFormData({
      ...formData,
      [option]: value
    });
    
    // Сбрасываем сообщения об ошибках при изменении формы
    setError(null);
  };

  // Функция для предпросмотра
  const handlePreview = async () => {
    if (previewLoading) return;
    
    setPreviewLoading(true);
    setError(null);
    setResultMessage(null);
    setSuccess(false);
    
    // Создаем FormData для отправки на сервер
    const formPayload = new FormData();
    for (const key in formData) {
      formPayload.append(key, formData[key]);
    }
    
    try {
      console.log('Отправка запроса на предпросмотр');
      
      // Проверяем URL - используем упрощенный маршрут
      let apiUrl = '/api/simple-preview';
      
      // Отправляем запрос на сервер с явным указанием данных
      const response = await axios({
        method: 'post',
        url: apiUrl,
        data: formPayload,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      console.log('Получен ответ от сервера:', response);
      
      // Проверяем ответ и обрабатываем его
      if (response.data && (response.data.message || response.data.status === 'success')) {
        // Показываем сообщение об успехе
        const successMsg = response.data.message || 'Предпросмотр успешно обработан';
        setResultMessage(successMsg);
        setSuccess(true);
        
        // Показываем всплывающее сообщение для подтверждения
        alert('Предпросмотр успешно обработан');
      } else {
        throw new Error('Неожиданный формат ответа от сервера');
      }
    } catch (err) {
      console.error('Ошибка при предпросмотре:', err);
      
      // Выводим полную информацию об ошибке для отладки
      console.log('Полная ошибка:', err);
      if (err.response) {
        console.log('Данные ответа:', err.response.data);
        console.log('Статус ответа:', err.response.status);
      }
      
      setError(err.response?.data?.message || err.message || 'Произошла ошибка при предпросмотре');
      setSuccess(false);
      
      // Показываем всплывающее сообщение об ошибке
      alert('Ошибка: ' + (err.response?.data?.message || err.message || 'Произошла ошибка при предпросмотре'));
    } finally {
      setPreviewLoading(false);
    }
  };

  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResultMessage(null);
    setSuccess(false);

    // Создаем FormData для отправки на сервер
    const formPayload = new FormData();
    for (const key in formData) {
      formPayload.append(key, formData[key]);
    }

    try {
      console.log('Отправка запроса на генерацию');
      
      // Проверяем URL - используем упрощенный маршрут
      let apiUrl = '/api/simple-generate';
      
      // Отправляем запрос на сервер с явным указанием данных
      const response = await axios({
        method: 'post',
        url: apiUrl,
        data: formPayload,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      console.log('Получен ответ от сервера:', response);

      // Проверяем ответ и обрабатываем его
      if (response.data && (response.data.message || response.data.status === 'success')) {
        // Показываем сообщение об успехе
        const successMsg = response.data.message || 'Пропись успешно сгенерирована';
        setResultMessage(successMsg);
        setSuccess(true);
        
        // Показываем всплывающее сообщение для подтверждения
        alert('Пропись успешно сгенерирована');
      } else {
        throw new Error('Неожиданный формат ответа от сервера');
      }
    } catch (err) {
      console.error('Ошибка при генерации:', err);
      
      // Выводим полную информацию об ошибке для отладки
      console.log('Полная ошибка:', err);
      if (err.response) {
        console.log('Данные ответа:', err.response.data);
        console.log('Статус ответа:', err.response.status);
      }
      
      setError(err.response?.data?.message || err.message || 'Произошла ошибка при генерации');
      setSuccess(false);
      
      // Показываем всплывающее сообщение об ошибке
      alert('Ошибка: ' + (err.response?.data?.message || err.message || 'Произошла ошибка при генерации'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2 className="form-title">Онлайн-генератор прописей для детей</h2>
      
      <div className="form-description">
        <p>Создавайте красивые прописи для обучения детей письму. Выберите варианты оформления и введите нужный текст.</p>
        </div>

      {/* Отображаем сообщение об успехе, если оно есть */}
      {success && resultMessage && (
        <div className="success-message" style={{ 
          backgroundColor: '#d4edda', 
          color: '#155724', 
          padding: '10px 15px',
          margin: '10px 0',
          borderRadius: '4px',
          border: '1px solid #c3e6cb'
        }}>
          {resultMessage}
        </div>
      )}
      
      {/* Отображаем сообщение об ошибке, если оно есть */}
      {error && (
        <div className="error-message" style={{ 
          backgroundColor: '#f8d7da', 
          color: '#721c24', 
          padding: '10px 15px',
          margin: '10px 0',
          borderRadius: '4px',
          border: '1px solid #f5c6cb'
        }}>
          <strong>Ошибка:</strong> {error}
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

        {/* Кнопки управления */}
        <div className="button-group">
          {/* Кнопка предпросмотра */}
          <button 
            type="button" 
            className="button button-secondary" 
            onClick={handlePreview} 
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
        </div>

        {/* Отображаем результат операции */}
        {resultMessage && (
          <div className="preview-container">
            <PreviewViewer message={resultMessage} />
          </div>
        )}
      </form>
    </div>
  );
};

export default PropisiForm; 