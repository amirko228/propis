import React from 'react';

const OptionCard = ({ title, img, selected, onClick }) => {
  return (
    <div
      className={`option-card ${selected ? 'selected' : ''}`}
      onClick={onClick}
      title={`Выбрать "${title}"`}
    >
      <img src={img} alt={title} />
      <div className="option-title">{title}</div>
      {selected && (
        <div className="option-selected">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6L9 17l-5-5"></path>
          </svg>
        </div>
      )}
    </div>
  );
};

export default OptionCard; 