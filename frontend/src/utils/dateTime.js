/**
 * 时间格式化工具函数
 * 统一使用北京时间（UTC+8）
 */

/**
 * 将时间转换为北京时间并格式化
 * @param {string|Date|number} value - 时间值（ISO 字符串、Date 对象或时间戳）
 * @param {string} format - 格式类型：'full' | 'date' | 'time' | 'datetime'
 * @returns {string} 格式化后的时间字符串
 */
export function formatBeijingTime(value, format = 'full') {
  if (!value) return "";
  
  let date;
  
  if (value instanceof Date) {
    date = value;
  } else if (typeof value === 'string') {
    // 如果字符串没有时区信息，假设它是 UTC 时间
    // 确保解析为 UTC 时间
    let normalizedValue = value;
    if (value.includes('T') && !value.includes('Z') && !value.includes('+') && !value.match(/[+-]\d{2}:\d{2}$/)) {
      // 没有时区信息，假设是 UTC 时间，添加 Z
      normalizedValue = value + 'Z';
    }
    date = new Date(normalizedValue);
  } else if (typeof value === 'number') {
    date = new Date(value);
  } else {
    return String(value);
  }
  
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  
  // 使用 Intl.DateTimeFormat 直接转换为北京时间（Asia/Shanghai）
  // 这是最可靠的方法，会自动处理时区转换
  // 无论输入是什么时区，都会正确转换为北京时间（UTC+8）
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',  // 指定为北京时间时区
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
  
  const parts = formatter.formatToParts(date);
  const year = parts.find(p => p.type === 'year')?.value || '';
  const month = parts.find(p => p.type === 'month')?.value || '';
  const day = parts.find(p => p.type === 'day')?.value || '';
  const hours = parts.find(p => p.type === 'hour')?.value || '';
  const minutes = parts.find(p => p.type === 'minute')?.value || '';
  const seconds = parts.find(p => p.type === 'second')?.value || '';
  
  switch (format) {
    case 'date':
      return `${year}/${month}/${day}`;
    case 'time':
      return `${hours}:${minutes}:${seconds}`;
    case 'datetime':
      return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
    case 'full':
    default:
      return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
  }
}

/**
 * 格式化时间（兼容旧代码，默认使用完整格式）
 */
export function formatTime(value) {
  return formatBeijingTime(value, 'full');
}

/**
 * 格式化日期（仅日期部分）
 */
export function formatDate(value) {
  return formatBeijingTime(value, 'date');
}

/**
 * 格式化时间（仅时间部分）
 */
export function formatTimeOnly(value) {
  return formatBeijingTime(value, 'time');
}

