import React from 'react';

// Đây là một file React.d.ts tối giản để giúp TypeScript nhận diện JSX
declare global {
  namespace JSX {
    interface Element {}
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}
