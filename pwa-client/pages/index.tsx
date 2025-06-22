import { useAuth } from './_app'
import LoginForm from '../components/LoginForm'
import BookLibrary from '../components/BookLibrary'
import Layout from '../components/Layout'
import Head from 'next/head'

export default function Home() {
  const { isAuthenticated } = useAuth()

  return (
    <>
      <Head>
        <title>Audiobook Player</title>
        <meta name="description" content="Stream your audiobooks on any device" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      
      <Layout>
        {isAuthenticated ? <BookLibrary /> : <LoginForm />}
      </Layout>
    </>
  )
} 