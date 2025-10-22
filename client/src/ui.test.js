/**
 * @jest-environment jsdom
 */

const fs = require('fs');
const path = require('path');

describe('UI Layout', () => {
  beforeAll(() => {
    // Read the HTML and CSS files
    const html = fs.readFileSync(path.resolve(__dirname, './index.html'), 'utf8');
    const css = fs.readFileSync(path.resolve(__dirname, './styles/style.css'), 'utf8');

    // Set up the DOM
    document.documentElement.innerHTML = html;

    // Apply the CSS
    const styleElement = document.createElement('style');
    styleElement.textContent = css;
    document.head.appendChild(styleElement);
  });

  test('container should have full-screen styles', () => {
    const container = document.querySelector('.container');
    const style = window.getComputedStyle(container);

    expect(style.width).toBe('100%');
    expect(style.height).toBe('100vh');
    expect(style.borderRadius).toBe('0');
  });
});
