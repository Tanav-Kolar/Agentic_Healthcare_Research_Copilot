import React from 'react';
import { Filter, Calendar, BookOpen, Database } from 'lucide-react';

const Sidebar = ({ filters, setFilters }) => {
  const studyTypes = [
    'Guideline',
    'Meta-analysis',
    'RCT',
    'Cohort',
    'Case Study',
    'Preprint'
  ];

  const handleTypeToggle = (type) => {
    const current = filters.study_types || [];
    if (current.includes(type)) {
      setFilters({ ...filters, study_types: current.filter(t => t !== type) });
    } else {
      setFilters({ ...filters, study_types: [...current, type] });
    }
  };

  return (
    <aside className="sidebar glass-panel animate-fade-in">
      <div className="flex items-center gap-2 mb-4">
        <Database className="text-accent-primary" size={24} />
        <h2 className="text-xl font-bold m-0">Lyra Research</h2>
      </div>

      <div className="filter-section">
        <label className="flex items-center gap-2 text-sm font-semibold text-text-secondary mb-3">
          <Calendar size={16} /> YEAR RANGE
        </label>
        <div className="flex flex-col gap-2">
          <input 
            type="number" 
            placeholder="From (e.g. 2022)" 
            value={filters.year_from || ''}
            onChange={(e) => setFilters({ ...filters, year_from: parseInt(e.target.value) || null })}
            className="w-full text-sm"
          />
          <input 
            type="number" 
            placeholder="To (e.g. 2024)" 
            value={filters.year_to || ''}
            onChange={(e) => setFilters({ ...filters, year_to: parseInt(e.target.value) || null })}
            className="w-full text-sm"
          />
        </div>
      </div>

      <div className="filter-section mt-6">
        <label className="flex items-center gap-2 text-sm font-semibold text-text-secondary mb-3">
          <BookOpen size={16} /> EVIDENCE TYPE
        </label>
        <div className="flex flex-col gap-2">
          {studyTypes.map(type => (
            <label key={type} className="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-white/5 transition-colors">
              <input 
                type="checkbox" 
                checked={(filters.study_types || []).includes(type)}
                onChange={() => handleTypeToggle(type)}
                className="w-4 h-4 accent-accent-primary"
              />
              <span className="text-sm text-text-primary">{type}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-white/5">
        <div className="flex items-center gap-2 text-xs text-text-secondary italic">
          <Filter size={12} />
          <span>Filters applied automatically to retrieval</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
