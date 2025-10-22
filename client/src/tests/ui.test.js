/**
 * @jest-environment jsdom
 */

const fs = require('fs');
const path = require('path');

describe('UI Layout', () => {
  beforeAll(() => {
    // Read the HTML and CSS files
    const html = fs.readFileSync(path.resolve(__dirname, '../index.html'), 'utf8');
    const css = fs.readFileSync(path.resolve(__dirname, '../styles/style.css'), 'utf8');

    // Set up the DOM
    document.documentElement.innerHTML = html;

    // Apply the CSS
    const styleElement = document.createElement('style');
    styleElement.textContent = css;
    document.head.appendChild(styleElement);
  });

  test('container should have a buffered width, max-width, and seamless background', () => {
    const container = document.querySelector('.container');
    const body = document.querySelector('body');
    const containerStyle = window.getComputedStyle(container);
    const bodyStyle = window.getComputedStyle(body);

    expect(containerStyle.width).toBe('65%');
    expect(containerStyle.maxWidth).toBe('1200px');
    expect(containerStyle.height).toBe('100vh');
    expect(containerStyle.borderRadius).toBe('0');
    expect(bodyStyle.backgroundColor).toBe(containerStyle.backgroundColor);
  });
});
