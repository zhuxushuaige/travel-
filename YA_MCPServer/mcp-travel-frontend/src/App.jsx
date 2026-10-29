// App.jsx
import { useState } from 'react';
import { Button, Input, InputNumber, Form, Card, Spin, message, Typography, List, Divider } from 'antd';

const { Title, Text, Paragraph } = Typography;

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [form] = Form.useForm();

  const handlePlanTrip = async (values) => {
    setLoading(true);
    try {
      // 调用 HTTP API（端口 8081）
      const response = await fetch('http://localhost:8081/create_travel_plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          city: values.city.trim(),
          days: Number(values.days),
          interests: (values.interests || "").trim(),
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.error) {
        message.error("规划失败: " + data.error);
        setResult(null);
      } else {
        setResult(data);
      }
    } catch (error) {
      console.error("Trip planning error:", error);
      message.error("请求失败: " + (error.message || "未知错误"));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '20px auto', padding: '0 16px' }}>
      <Card title="智能旅行规划" style={{ marginBottom: 24 }}>
        <Form form={form} onFinish={handlePlanTrip} layout="vertical">
          <Form.Item
            name="city"
            label="目的地"
            rules={[{ required: true, message: '请输入城市名称' }]}
          >
            <Input placeholder="例如：杭州、武汉、上海" />
          </Form.Item>

          <Form.Item
            name="days"
            label="旅行天数"
            initialValue={3}
            rules={[
              { required: true, message: '请输入天数' },
              { type: 'number', min: 1, max: 7, message: '天数需在 1-7 之间' }
            ]}
          >
            <InputNumber 
              min={1} 
              max={7} 
              placeholder="1-7" 
              style={{ width: '100%' }} 
            />
          </Form.Item>

          <Form.Item
            name="interests"
            label="兴趣标签（逗号或空格分隔）"
          >
            <Input placeholder="例如：博物馆,历史 或 自然 公园 美食" />
          </Form.Item>

          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            block
            size="large"
          >
            生成旅行计划
          </Button>
        </Form>
      </Card>

      {loading && (
        <Card>
          <Spin tip="正在为您规划行程..." />
        </Card>
      )}

      {result && !result.error && (
        <Card title={`✈️ ${result.city} ${result.total_days}日旅行计划`}>

          {/* 酒店信息 */}
          <Title level={5}>🏨 推荐住宿</Title>
          <Paragraph>
            <Text strong>{result.hotel.name}</Text><br />
            📍 {result.hotel.address}<br />
            📏 距景点中心 {result.hotel.distance_to_center_km} km
            {result.hotel.rating !== "N/A" && ` | ⭐ ${result.hotel.rating}`}
          </Paragraph>

          {/* 天气概览 */}
          <Title level={5}>🌤️ 天气概览</Title>
          <Paragraph>{result.weather_overview}</Paragraph>

          <Divider />

          {/* 每日行程 */}
          <Title level={5}>🗓️ 每日行程安排</Title>
          <List
            dataSource={result.itinerary}
            renderItem={(day) => (
              <List.Item key={day.day}>
                <Card size="small" title={`第 ${day.day} 天 (${day.date}) - ${day.weather}`}>
                  <Paragraph>
                    <Text strong>景点：</Text>
                    {day.attractions.join(' → ')}
                  </Paragraph>
                  <Paragraph>
                    <Text strong>路线建议：</Text>
                    {day.routes.map((route, idx) => (
                      <div key={idx} style={{ marginBottom: 4 }}>
                        • 从 {route.from} 到 {route.to}：{route.transport}
                        {route.duration_min && route.distance_km && (
                          <Text type="secondary">（约 {route.duration_min} 分钟，{route.distance_km} km）</Text>
                        )}
                      </div>
                    ))}
                  </Paragraph>
                </Card>
              </List.Item>
            )}
          />

          <Divider />
          <Text type="secondary">{result.note}</Text>
        </Card>
      )}
    </div>
  );
}

export default App;