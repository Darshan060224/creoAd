import React from 'react';

function Error({ statusCode, errorMessage }) {
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Error {statusCode}</h1>
      <p>{errorMessage || 'An unexpected error occurred'}</p>
    </div>
  );
}

Error.getInitialProps = ({ res, err }) => {
  const statusCode = res ? res.statusCode : err ? err.statusCode : 404;
  return { statusCode, errorMessage: err ? err.message : null };
};

export default Error;
