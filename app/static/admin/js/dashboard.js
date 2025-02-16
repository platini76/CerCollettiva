// static/admin/js/dashboard.js

import React from 'react';
import { createRoot } from 'react-dom/client';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Users, Battery, Zap, Share2, AlertCircle, Sun, Home, Bell } from 'lucide-react';

const AdminDashboard = () => {
  // Recupera i dati passati da Django attraverso window.dashboardData
  const { stats, cerEnergyData, hourlyData, recentAlerts } = window.dashboardData || {
    stats: {
      total_users: 0,
      active_plants: 0,
      active_alerts: 0,
      active_cer: 0
    },
    cerEnergyData: [],
    hourlyData: [],
    recentAlerts: []
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('it-IT').format(num);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Sezione 1: Overview del Sistema */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">Utenti Totali</p>
              <p className="text-2xl font-bold">{formatNumber(stats.total_users)}</p>
            </div>
            <Users className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">Impianti Attivi</p>
              <p className="text-2xl font-bold">{formatNumber(stats.active_plants)}</p>
            </div>
            <Sun className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">Alert Attivi</p>
              <p className="text-2xl font-bold">{formatNumber(stats.active_alerts)}</p>
            </div>
            <AlertCircle className="h-8 w-8 text-red-500" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">CER Attive</p>
              <p className="text-2xl font-bold">{formatNumber(stats.active_cer)}</p>
            </div>
            <Home className="h-8 w-8 text-purple-500" />
          </div>
        </div>
      </div>

      {/* Sezione 2: Metriche Energetiche */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Grafico confronto energie per CER */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Confronto Energie per CER</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cerEnergyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis yAxisId="left" orientation="left" />
                <YAxis yAxisId="right" orientation="right" domain={[0, 100]} />
                <Tooltip
                  formatter={(value, name) => [
                    `${formatNumber(value)} ${name.includes('%') ? '%' : 'kWh'}`,
                    name
                  ]}
                />
                <Legend />
                <Bar yAxisId="left" dataKey="prodotta" name="Energia Prodotta" fill="#FBBF24" />
                <Bar yAxisId="left" dataKey="consumata" name="Energia Consumata" fill="#3B82F6" />
                <Bar yAxisId="left" dataKey="condivisa" name="Energia Condivisa" fill="#10B981" />
                <Line 
                  yAxisId="right" 
                  type="monotone" 
                  dataKey="percentualeCondivisione" 
                  name="% Condivisione" 
                  stroke="#7C3AED" 
                  strokeWidth={2} 
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Grafico andamento orario */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Andamento Orario CER</h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="ora" />
                <YAxis />
                <Tooltip 
                  formatter={(value) => [`${formatNumber(value)} kWh`]}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="prodotta" 
                  name="Prodotta" 
                  stroke="#FBBF24" 
                  strokeWidth={2} 
                />
                <Line 
                  type="monotone" 
                  dataKey="consumata" 
                  name="Consumata" 
                  stroke="#3B82F6" 
                  strokeWidth={2} 
                />
                <Line 
                  type="monotone" 
                  dataKey="condivisa" 
                  name="Condivisa" 
                  stroke="#10B981" 
                  strokeWidth={2} 
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Sezione 3: Alert e Azioni Rapide */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lista ultimi alert */}
        <div className="lg:col-span-2 bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Ultimi Alert</h2>
          <div className="space-y-2">
            {recentAlerts.map((alert, index) => (
              <div key={index} className="flex items-center justify-between border-b pb-2">
                <div className="flex items-center">
                  <span className={`w-2 h-2 rounded-full mr-2 ${
                    alert.severity === 'critical' ? 'bg-red-500' :
                    alert.severity === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
                  }`}></span>
                  <span>{alert.message}</span>
                </div>
                <span className="text-gray-500 text-sm">
                  {new Date(alert.created_at).toLocaleString('it-IT')}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Azioni Rapide</h2>
          <div className="space-y-3">
            <button 
              onClick={() => window.location.href = '/admin/users/customuser/'}
              className="w-full bg-blue-500 text-white p-3 rounded-lg hover:bg-blue-600 transition-colors flex items-center justify-center"
            >
              <Users className="h-5 w-5 mr-2" />
              Gestione Utenti
            </button>
            <button 
              onClick={() => window.location.href = '/admin/core/cerconfiguration/'}
              className="w-full bg-green-500 text-white p-3 rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center"
            >
              <Home className="h-5 w-5 mr-2" />
              Gestione CER
            </button>
            <button 
              onClick={() => window.location.href = '/admin/core/plant/'}
              className="w-full bg-purple-500 text-white p-3 rounded-lg hover:bg-purple-600 transition-colors flex items-center justify-center"
            >
              <Sun className="h-5 w-5 mr-2" />
              Gestione Impianti
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Inizializzazione dell'applicazione React
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('react-admin-dashboard');
  if (container) {
    const root = createRoot(container);
    root.render(<AdminDashboard />);
  }
});

export default AdminDashboard;