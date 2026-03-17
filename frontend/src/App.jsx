import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Pairing from './pages/Pairing'
import Cropping from './pages/Cropping'
import VideoExtraction from './pages/VideoExtraction'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/pairing" element={<Pairing />} />
        <Route path="/cropping" element={<Cropping />} />
        <Route path="/video" element={<VideoExtraction />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
