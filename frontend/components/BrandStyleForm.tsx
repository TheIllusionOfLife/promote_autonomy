'use client';

import { useState, useEffect } from 'react';
import type { BrandStyle, BrandColor, BrandTone } from '@/lib/types';

interface BrandStyleFormProps {
  value: BrandStyle | null;
  onChange: (style: BrandStyle | null) => void;
}

export default function BrandStyleForm({ value, onChange }: BrandStyleFormProps) {
  const [colors, setColors] = useState<BrandColor[]>(
    value?.colors || [{ hex_code: '4D18C9', name: '', usage: 'primary' }]
  );
  const [tone, setTone] = useState<BrandTone>(value?.tone || 'professional');
  const [tagline, setTagline] = useState(value?.tagline || '');

  // Sync state with prop changes
  useEffect(() => {
    if (value) {
      setColors(value.colors);
      setTone(value.tone);
      setTagline(value.tagline || '');
    } else {
      // Reset to defaults when value is null
      setColors([{ hex_code: '4D18C9', name: '', usage: 'primary' }]);
      setTone('professional');
      setTagline('');
    }
  }, [value]);

  const handleUpdate = (
    newColors: BrandColor[],
    newTone: BrandTone,
    newTagline: string
  ) => {
    setColors(newColors);
    setTone(newTone);
    setTagline(newTagline);

    onChange({
      colors: newColors,
      tone: newTone,
      tagline: newTagline || undefined,
      logo_url: value?.logo_url, // Preserve existing logo_url
    });
  };

  const addColor = () => {
    if (colors.length < 5) {
      const newColors = [
        ...colors,
        { hex_code: '000000', name: '', usage: 'general' as const },
      ];
      handleUpdate(newColors, tone, tagline);
    }
  };

  const updateColor = (
    index: number,
    field: keyof BrandColor,
    value: string
  ) => {
    // Validate hex code (must be exactly 6 hex characters)
    if (field === 'hex_code') {
      const hexPattern = /^[0-9A-Fa-f]{6}$/;
      if (!hexPattern.test(value)) {
        // Don't update if invalid hex code
        return;
      }
    }

    // Prevent multiple primary colors
    if (field === 'usage' && value === 'primary') {
      const existingPrimaryIndex = colors.findIndex(
        (c, i) => i !== index && c.usage === 'primary'
      );
      if (existingPrimaryIndex !== -1) {
        // If another color is already primary, make it general
        const newColors: BrandColor[] = colors.map((color, i) => {
          if (i === existingPrimaryIndex) {
            return { ...color, usage: 'general' };
          } else if (i === index) {
            return { ...color, usage: value as BrandColor['usage'] };
          }
          return color;
        });
        handleUpdate(newColors, tone, tagline);
        return;
      }
    }

    const newColors = colors.map((color, i) =>
      i === index ? { ...color, [field]: value } : color
    );
    handleUpdate(newColors, tone, tagline);
  };

  const removeColor = (index: number) => {
    if (colors.length > 1) {
      const newColors = colors.filter((_, i) => i !== index);
      handleUpdate(newColors, tone, tagline);
    }
  };

  return (
    <div className="border border-gray-300 rounded-lg p-6 space-y-6 bg-white shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Brand Style Guide
        </h3>
      </div>

      {/* Tone Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Brand Tone
        </label>
        <select
          value={tone}
          onChange={(e) => handleUpdate(colors, e.target.value as BrandTone, tagline)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="professional">Professional - Corporate, formal language</option>
          <option value="casual">Casual - Friendly, approachable tone</option>
          <option value="playful">Playful - Fun, energetic, emoji-rich</option>
          <option value="luxury">Luxury - Elegant, sophisticated</option>
          <option value="technical">Technical - Precise, expert terminology</option>
        </select>
      </div>

      {/* Brand Colors */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Brand Colors (1-5 colors)
        </label>
        <p className="text-xs text-gray-500 mb-3">
          Pick color → Give it a name → Select usage type (Primary/Accent/etc.)
        </p>
        <div className="space-y-2">
          {colors.map((color, index) => (
            <div key={index} className="flex items-center gap-2">
              <input
                type="color"
                value={`#${color.hex_code}`}
                onChange={(e) =>
                  updateColor(index, 'hex_code', e.target.value.slice(1).toUpperCase())
                }
                className="w-14 h-10 rounded cursor-pointer border border-gray-300"
                title="Pick color"
              />
              <input
                type="text"
                placeholder="Name this color (e.g., Brand Blue)"
                value={color.name}
                onChange={(e) => updateColor(index, 'name', e.target.value)}
                maxLength={30}
                className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                title="Give this color a descriptive name"
              />
              <select
                value={color.usage}
                onChange={(e) => updateColor(index, 'usage', e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="primary">Primary</option>
                <option value="accent">Accent</option>
                <option value="background">Background</option>
                <option value="general">General</option>
              </select>
              {colors.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeColor(index)}
                  className="text-red-600 hover:text-red-800 px-2 py-1 font-bold text-xl"
                  title="Remove color"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
        {colors.length < 5 && (
          <button
            type="button"
            onClick={addColor}
            className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            + Add Color
          </button>
        )}
      </div>

      {/* Tagline */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Brand Tagline (Optional)
        </label>
        <input
          type="text"
          placeholder="Your brand tagline (e.g., Innovation starts here)"
          value={tagline}
          onChange={(e) => handleUpdate(colors, tone, e.target.value)}
          maxLength={100}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          {tagline.length}/100 characters
          {tagline.length > 0 && ' - Will be included in captions'}
        </p>
      </div>

      {/* Preview */}
      <div className="pt-4 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Preview</h4>
        <div className="flex flex-wrap gap-2">
          {colors.map((color, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-2 rounded-md border border-gray-200 bg-gray-50"
            >
              <div
                className="w-6 h-6 rounded border border-gray-300"
                style={{ backgroundColor: `#${color.hex_code}` }}
              />
              <span className="text-sm font-medium text-gray-700">
                {color.name || 'Unnamed'}
              </span>
              <span className="text-xs text-gray-500">({color.usage})</span>
            </div>
          ))}
        </div>
        <p className="text-sm text-gray-600 mt-2">
          <strong>Tone:</strong> {tone.charAt(0).toUpperCase() + tone.slice(1)}
        </p>
        {tagline && (
          <p className="text-sm text-gray-600 mt-1">
            <strong>Tagline:</strong> {tagline}
          </p>
        )}
      </div>
    </div>
  );
}
