// Enhanced logging system with beautiful styling
const logs = [];

function log(msg, type = 'info') {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('th-TH', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
  
  // สร้าง HTML สำหรับ log entry ที่สวยงาม
  const logEntry = {
    time: timeStr,
    message: msg,
    type: type,
    id: Date.now() + Math.random()
  };
  
  // เพิ่ม log entry ใหม่ที่ด้านบน (ไม่ซ้ำกัน)
  const existingIndex = logs.findIndex(log => log.message === msg && log.type === type);
  if (existingIndex === -1) {
    logs.unshift(logEntry);
  }
  
  // จำกัดจำนวน logs ไม่เกิน 50 รายการ
  if (logs.length > 50) logs.pop();
  
  // อัพเดท UI
  updateLogDisplay();
  
  // ส่ง log ไปฝั่ง server (ถ้ามี)
  try {
    fetch('/api/client_log', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ 
        message: msg, 
        timestamp: timeStr,
        type: type 
      })
    }).catch(() => {}); // เงียบๆ ถ้า server ไม่ตอบสนอง
  } catch (e) {
    // ไม่ต้องทำอะไรถ้า fetch ไม่สำเร็จ
  }
}

function updateLogDisplay() {
  const logElement = document.getElementById('log');
  if (!logElement) return;
  
  // สร้าง HTML สำหรับแสดง logs แบบสวยงาม
  const logHTML = logs.map((entry, index) => {
    const typeClass = getLogTypeClass(entry.type);
    const icon = getLogIcon(entry.type);
    const isLatest = index === 0;
    
    return `
      <div class="log-entry ${typeClass} ${isLatest ? 'log-latest' : ''}" data-type="${entry.type}">
        <div class="log-left">
          <span class="log-time">${entry.time}</span>
          <span class="log-icon">${icon}</span>
        </div>
        <div class="log-content">
          <span class="log-message">${entry.message}</span>
          ${isLatest ? '<div class="log-pulse"></div>' : ''}
        </div>
      </div>
    `;
  }).join('');
  
  logElement.innerHTML = logHTML;
  
  // เลื่อน log ใหม่ให้เห็น
  if (logs.length > 0) {
    logElement.scrollTop = 0;
  }
}

function getLogTypeClass(type) {
  const typeClasses = {
    'info': 'log-info',
    'success': 'log-success', 
    'warning': 'log-warning',
    'error': 'log-error',
    'route': 'log-route',
    'search': 'log-search'
  };
  return typeClasses[type] || 'log-info';
}

function getLogIcon(type) {
  const icons = {
    'info': 'ℹ️',
    'success': '✅',
    'warning': '⚠️', 
    'error': '❌',
    'route': '🚗',
    'search': '🔍'
  };
  return icons[type] || 'ℹ️';
}

// ฟังก์ชันสำหรับ log แต่ละประเภท
function logInfo(msg) { log(msg, 'info'); }
function logSuccess(msg) { log(msg, 'success'); }
function logWarning(msg) { log(msg, 'warning'); }
function logError(msg) { log(msg, 'error'); }
function logRoute(msg) { log(msg, 'route'); }
function logSearch(msg) { log(msg, 'search'); }

// ฟังก์ชันล้าง logs
function clearLogs() {
  logs.length = 0;
  updateLogDisplay();
}

// CSS Styles สำหรับ log display (เพิ่มใน <style> tag หรือไฟล์ CSS)
const logStyles = `
<style>
#log {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  max-height: 300px;
  overflow-y: auto;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  backdrop-filter: blur(10px);
  position: relative;
}

#log::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.1);
  border-radius: 16px;
  pointer-events: none;
}

.log-entry {
  display: flex;
  align-items: flex-start;
  padding: 12px 16px;
  margin-bottom: 8px;
  border-radius: 12px;
  transition: all 0.3s ease;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.3);
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  position: relative;
  overflow: hidden;
}

.log-entry::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--log-color, #17a2b8);
  transition: width 0.3s ease;
}

.log-entry:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}

.log-entry:hover::before {
  width: 8px;
}

.log-latest {
  animation: slideIn 0.5s ease, pulse 2s infinite;
  box-shadow: 0 6px 20px rgba(0,123,255,0.3);
}

.log-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-right: 12px;
  min-width: 70px;
}

.log-time {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
  color: #666;
  font-size: 11px;
  font-weight: 500;
  background: rgba(0,0,0,0.05);
  padding: 2px 6px;
  border-radius: 6px;
  margin-bottom: 4px;
}

.log-icon {
  font-size: 18px;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
}

.log-content {
  flex: 1;
  position: relative;
}

.log-message {
  color: #2d3748;
  font-weight: 500;
  line-height: 1.4;
  word-break: break-word;
}

.log-pulse {
  position: absolute;
  right: -10px;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  background: #00d4aa;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.log-info {
  --log-color: #17a2b8;
}

.log-success {
  --log-color: #28a745;
}

.log-warning {
  --log-color: #ffc107;
}

.log-error {
  --log-color: #dc3545;
}

.log-route {
  --log-color: #007bff;
}

.log-search {
  --log-color: #6f42c1;
}

#log::-webkit-scrollbar {
  width: 8px;
}

#log::-webkit-scrollbar-track {
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
}

#log::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.3);
  border-radius: 10px;
  transition: background 0.3s ease;
}

#log::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.5);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(0, 212, 170, 0.7);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(0, 212, 170, 0);
  }
}
</style>
`;

function updateRouteStopsList(stops) {
  const listElement = document.getElementById('route-stops-list');
  if (!listElement) return;

  if (!stops || stops.length === 0) {
    const initialText = stops === null ? 'ผลลัพธ์จุดแวะพักจะแสดงที่นี่' : 'ไม่พบจุดแวะพักตามเงื่อนไขที่เลือก';
    listElement.innerHTML = `<p class="placeholder-text">${initialText}</p>`;
    return;
  }

  const stopsHTML = stops.map((p, i) => {
    const detour = p.detour_minutes_est != null ? 
      ` • <span style="color: #ef4444;">เบี่ยง ~${p.detour_minutes_est} นาที</span>` : "";
    return `
      <div class='place'>
        <div class='name'>${i + 1}. ${p.name}</div>
        <div class='meta'>⭐ ${p.rating || '-'} (${p.user_ratings_total || 0} รีวิว)${detour}</div>
        ${p.categories ? `<div class='meta' style="color: var(--accent);">📂 ${p.categories.join(', ')}</div>` : ""}
        <div style='margin-top:8px'>
          <a href="${p.map_url}" target="_blank">Google Maps</a>
          ${p.website ? ` • <a href="${p.website}" target="_blank">เว็บไซต์</a>` : ""}
        </div>
      </div>
    `;
  }).join('');
  listElement.innerHTML = stopsHTML;
}

// Updated planRoute function with beautiful logging
async function planRoute() {
  clearMarkers();
  updateRouteStopsList([]); // เคลียร์รายการเก่าก่อนค้นหา

  const origin = document.getElementById('origin').value.trim();
  const dest = document.getElementById('dest').value.trim();
  
  if (!origin || !dest) { 
    logWarning('กรุณากรอกจุดเริ่มต้นและจุดหมายปลายทาง');
    // alert('กรอกจุดเริ่มและจุดหมายก่อนนะ'); // ใช้ log แทน alert จะดีกว่า
    return; 
  }
  
  const categories = [...sel]; // สมมติว่ามีตัวแปร sel อยู่แล้ว
  logSearch('🔍 เริ่มค้นหาเส้นทางและจุดแวะพัก...');
  
  try {
    const response = await fetch('/api/route_suggestions', {
      method: 'POST', 
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ 
        origin: origin, 
        destination: dest, 
        categories: categories 
      })
    });
    
    const data = await response.json();
    
    if (!data || data.error) { 
      logError(`❌ เกิดข้อผิดพลาด: ${data.error || 'ไม่สามารถค้นหาเส้นทางได้'}`);
      updateRouteStopsList([]); // แสดงข้อความ "ไม่พบ"
      // alert(data.error || 'เกิดข้อผิดพลาด');
      return; 
    }
    
    // วาดเส้นทาง
    if (data.route && data.route.polyline) {
      drawRoute(data.route.polyline);
      logRoute('🗺️ วาดเส้นทางบนแผนที่เรียบร้อยแล้ว');
    }
    
    // เพิ่มจุดแวะ
    if (data.stops && data.stops.length > 0) {
      data.stops.forEach((place, index) => addPlace(place, index + 1));
      logSuccess(`📍 พบจุดแวะพักที่น่าสนใจ ${data.stops.length} แห่ง`);
      updateRouteStopsList(data.stops); // แสดงผลรายการ
    } else {
      logWarning('⚠️ ไม่พบจุดแวะพักตามเงื่อนไขที่เลือก');
      updateRouteStopsList([]); // แสดงข้อความ "ไม่พบ"
    }
    
    // แสดงสรุปเส้นทาง
    if (data.route && data.route.distance_text && data.route.duration_text) {
      const summary = `🚗 ระยะทาง: ${data.route.distance_text} • ⏱️ เวลา: ${data.route.duration_text}`;
      logRoute(summary);
    }
    
    logSuccess('🎉 วางแผนเส้นทางเสร็จสมบูรณ์!');
    
  } catch (error) {
    logError(`❌ เกิดข้อผิดพลาดในการเชื่อมต่อ: ${error.message}`);
    updateRouteStopsList([]); // แสดงข้อความ "ไม่พบ"
    console.error('Route planning error:', error);
  }
}

// อย่าลืมเพิ่ม CSS styles ใน HTML
document.head.insertAdjacentHTML('beforeend', logStyles);